using System.Text;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Encodings.Web;

// ============================================================================
// Export all structural metadata from data.win to datamine/output/meta/
//
// Exports:
//   object_index_map.json  - {index: name} for all GameObjects
//   object_tree.json       - {parent: [children]} inheritance
//   sprite_index_map.json  - {index: name} for all Sprites
//   sound_index_map.json   - {index: name} for all Sounds
//
// Self-contained: derives output path from ScriptPath, no external config.
// ============================================================================

EnsureDataLoaded();

if (Data.IsYYC())
{
    ScriptError("The opened game uses YYC: no code is available.");
    return;
}

// ── Output path: datamine/output/meta/ ────────────────────────────
string scriptDir = Path.GetDirectoryName(ScriptPath);
string outputFolder = Path.GetFullPath(Path.Combine(scriptDir, "output", "meta"));

if (!Directory.Exists(outputFolder))
    Directory.CreateDirectory(outputFolder);

var jsonOptions = new JsonSerializerOptions
{
    WriteIndented = true,
    Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
};

int exported = 0;

// ── 1. Object Index Map ──────────────────────────────────────────
{
    var data = Data.GameObjects
        .Select((obj, i) => new { Index = i, Name = obj.Name.Content })
        .OrderBy(x => x.Index)
        .ToDictionary(x => x.Index.ToString(), x => x.Name);

    string path = Path.Combine(outputFolder, "object_index_map.json");
    File.WriteAllText(path, JsonSerializer.Serialize(data, jsonOptions));
    exported++;
}

// ── 2. Object Tree ───────────────────────────────────────────────
{
    var tree = Data.GameObjects
        .Where(o => o.ParentId is not null)
        .GroupBy(o => o.ParentId.Name.Content)
        .ToDictionary(g => g.Key, g => g.Select(o => o.Name.Content).OrderBy(n => n).ToList());

    var sorted = new SortedDictionary<string, List<string>>(tree);

    string path = Path.Combine(outputFolder, "object_tree.json");
    File.WriteAllText(path, JsonSerializer.Serialize(sorted, jsonOptions));
    exported++;
}

// ── 3. Sprite Index Map ──────────────────────────────────────────
{
    var data = Data.Sprites
        .Select((spr, i) => new { Index = i, Name = spr.Name.Content })
        .OrderBy(x => x.Index)
        .ToDictionary(x => x.Index.ToString(), x => x.Name);

    string path = Path.Combine(outputFolder, "sprite_index_map.json");
    File.WriteAllText(path, JsonSerializer.Serialize(data, jsonOptions));
    exported++;
}

// ── 4. Sound Index Map ───────────────────────────────────────────
{
    var data = Data.Sounds
        .Select((snd, i) => new { Index = i, Name = snd.Name.Content })
        .OrderBy(x => x.Index)
        .ToDictionary(x => x.Index.ToString(), x => x.Name);

    string path = Path.Combine(outputFolder, "sound_index_map.json");
    File.WriteAllText(path, JsonSerializer.Serialize(data, jsonOptions));
    exported++;
}

ScriptMessage($"Exported {exported} meta files to:\n{outputFolder}");
