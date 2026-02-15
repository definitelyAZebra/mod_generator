// dump_gml.csx — Dump all decompiled GML code to CodeEntries/
//
// Based on UndertaleModTool's built-in ExportAllCode.csx / ExportAllCodeSync.csx,
// adapted for CLI mode with these additions:
//   1. Filters out child entries (ParentEntry != null) — main cause of decompile failures
//   2. Handles duplicates separately in a Duplicates/ subfolder
//   3. Uses Parallel.ForEach for speed (matches official ExportAllCode.csx)
//   4. Falls back to disassembly on decompile failure
//   5. Truncates filenames exceeding MAX_PATH (Windows)
//   6. Writes a manifest of all entries + their filenames
//
// Usage:
//   UndertaleModCli.exe load data.win -s dump_gml.csx
//
// Output dir is derived from ScriptPath → sibling "output/CodeEntries/"

using System;
using System.IO;
using System.Text;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using UndertaleModLib;
using UndertaleModLib.Decompiler;

// ── Safety checks ─────────────────────────────────────────────────
EnsureDataLoaded();

if (Data.IsYYC())
{
    ScriptError("The opened game uses YYC: no code is available.");
    return;
}

// ── Resolve output directories ────────────────────────────────────
string scriptDir = Path.GetDirectoryName(ScriptPath);
string outDir = Path.Combine(scriptDir, "output", "CodeEntries");
string failedDir = Path.Combine(outDir, "Failed");
string duplicatesDir = Path.Combine(outDir, "Duplicates");
string duplicatesFailedDir = Path.Combine(duplicatesDir, "Failed");
Directory.CreateDirectory(outDir);

// ── Settings ──────────────────────────────────────────────────────
const int MAX_FILENAME_LEN = 200;  // Leave room for path prefix + .gml extension

// ── Decompiler setup ──────────────────────────────────────────────
GlobalDecompileContext globalDecompileContext = new(Data);
Underanalyzer.Decompiler.IDecompileSettings decompilerSettings = Data.ToolInfo.DecompilerSettings;

// ── Separate parent entries from child/duplicate entries ──────────
// Key insight from official UTMT: child entries (ParentEntry != null) are
// sub-entries that reference another code entry. Decompiling them directly
// often fails or produces garbage. The official scripts skip them entirely
// or handle them in a separate "Duplicates" folder.
List<UndertaleCode> mainEntries = Data.Code.Where(c => c.ParentEntry is null).ToList();
List<UndertaleCode> childEntries = Data.Code.Where(c => c.ParentEntry is not null).ToList();

int totalAll = Data.Code.Count;
int totalMain = mainEntries.Count;
int totalChild = childEntries.Count;

ScriptMessage($"Total code entries: {totalAll}");
ScriptMessage($"  Main entries (ParentEntry == null): {totalMain}");
ScriptMessage($"  Child/duplicate entries:            {totalChild}");
ScriptMessage($"Dumping main entries to {outDir}...");

// ── Thread-safe counters ──────────────────────────────────────────
int mainSuccess = 0;
int mainFailed = 0;
int truncated = 0;
var errors = new ConcurrentBag<string>();
var manifest = new ConcurrentBag<string>();

// ── Helper: build safe filename ───────────────────────────────────
string SafeFilename(string name, ref int truncCount)
{
    string baseName = name;
    if (baseName.Length > MAX_FILENAME_LEN)
    {
        string hash = Math.Abs(baseName.GetHashCode()).ToString("X8");
        baseName = baseName.Substring(0, MAX_FILENAME_LEN - 9) + "_" + hash;
        System.Threading.Interlocked.Increment(ref truncCount);
    }
    return baseName + ".gml";
}

// ── Helper: decompile a single entry ──────────────────────────────
string DecompileEntry(UndertaleCode code)
{
    return new Underanalyzer.Decompiler.DecompileContext(
        globalDecompileContext, code, decompilerSettings
    ).DecompileToString();
}

// ── Helper: disassemble fallback ──────────────────────────────────
string DisassembleEntry(UndertaleCode code)
{
    return code.Disassemble(Data.Variables, Data.CodeLocals?.For(code));
}

// ── Phase 1: Dump main entries (parallel) ─────────────────────────
Parallel.ForEach(mainEntries, code =>
{
    string name = code.Name?.Content ?? "<null>";
    string filename = SafeFilename(name, ref truncated);
    manifest.Add($"{name}\t{filename}");

    string path = Path.Combine(outDir, filename);
    try
    {
        string decompiled = DecompileEntry(code);
        File.WriteAllText(path, decompiled, Encoding.UTF8);
        System.Threading.Interlocked.Increment(ref mainSuccess);
    }
    catch (Exception ex)
    {
        // Decompile failed — try disassembly fallback, write to Failed/ subfolder
        System.Threading.Interlocked.Increment(ref mainFailed);
        errors.Add($"{name}: {ex.Message}");

        if (!Directory.Exists(failedDir))
            Directory.CreateDirectory(failedDir);

        string failedPath = Path.Combine(failedDir, filename);
        try
        {
            // Write full exception trace (matches official UTMT format) + disassembly
            var sb = new StringBuilder();
            sb.AppendLine("/*");
            sb.AppendLine("DECOMPILER FAILED!");
            sb.AppendLine();
            sb.AppendLine(ex.ToString());
            sb.AppendLine("*/");
            sb.AppendLine();
            sb.AppendLine("// === DISASSEMBLY FALLBACK ===");
            try
            {
                sb.AppendLine(DisassembleEntry(code));
            }
            catch (Exception disEx)
            {
                sb.AppendLine($"// DISASSEMBLY ALSO FAILED: {disEx.Message}");
            }
            File.WriteAllText(failedPath, sb.ToString(), Encoding.UTF8);
        }
        catch
        {
            // Even failed file write failed — just record error
            errors.Add($"{name}: FILE WRITE ERROR");
        }
    }
});

ScriptMessage($"Main entries done: {mainSuccess} ok, {mainFailed} failed, {truncated} truncated");

// ── Phase 2: Dump child/duplicate entries ─────────────────────────
int dupSuccess = 0;
int dupFailed = 0;

if (childEntries.Count > 0)
{
    ScriptMessage($"Dumping {totalChild} child/duplicate entries to {duplicatesDir}...");
    Directory.CreateDirectory(duplicatesDir);

    Parallel.ForEach(childEntries, code =>
    {
        string name = code.Name?.Content ?? "<null>";
        string filename = SafeFilename(name, ref truncated);
        manifest.Add($"{name}\t{Path.Combine("Duplicates", filename)}");

        string path = Path.Combine(duplicatesDir, filename);
        try
        {
            string decompiled = DecompileEntry(code);
            File.WriteAllText(path, decompiled, Encoding.UTF8);
            System.Threading.Interlocked.Increment(ref dupSuccess);
        }
        catch (Exception ex)
        {
            System.Threading.Interlocked.Increment(ref dupFailed);

            if (!Directory.Exists(duplicatesFailedDir))
                Directory.CreateDirectory(duplicatesFailedDir);

            string failedPath = Path.Combine(duplicatesFailedDir, filename);
            try
            {
                File.WriteAllText(failedPath,
                    $"/*\nDECOMPILER FAILED!\n\n{ex}\n*/\n", Encoding.UTF8);
            }
            catch { }
        }
    });

    ScriptMessage($"Duplicates done: {dupSuccess} ok, {dupFailed} failed");
}

// ── Write manifest ────────────────────────────────────────────────
var sortedManifest = manifest.OrderBy(x => x).ToList();
string manifestPath = Path.Combine(outDir, "_manifest.tsv");
File.WriteAllText(manifestPath,
    "original_name\tfilename\n" + string.Join("\n", sortedManifest),
    Encoding.UTF8);

// ── Write error log ───────────────────────────────────────────────
var sortedErrors = errors.OrderBy(x => x).ToList();
if (sortedErrors.Count > 0)
{
    string errorPath = Path.Combine(outDir, "_errors.log");
    File.WriteAllText(errorPath, string.Join("\n", sortedErrors), Encoding.UTF8);
}

// ── Summary ───────────────────────────────────────────────────────
ScriptMessage($"\nDone!");
ScriptMessage($"  Total entries:    {totalAll}");
ScriptMessage($"  Main entries:     {totalMain} ({mainSuccess} ok, {mainFailed} failed)");
ScriptMessage($"  Duplicate entries:{totalChild} ({dupSuccess} ok, {dupFailed} failed)");
ScriptMessage($"  Truncated names:  {truncated}");
ScriptMessage($"  Total errors:     {sortedErrors.Count}");
ScriptMessage($"  Manifest:         {manifestPath}");
ScriptMessage($"  Output:           {outDir}");
if (mainFailed > 0)
    ScriptMessage($"  Failed dir:       {failedDir}");
if (dupFailed > 0)
    ScriptMessage($"  Dup failed dir:   {duplicatesFailedDir}");
