# gml_Object_o_inv_left_hand_Other_16.gml

## 文件位置
`datamine/output/CodeEntries/gml_Object_o_inv_left_hand_Other_16.gml`

## 事件类型
Other Event 16 (Animation End)

## 代码内容

```gml
with (children)
{
    if (scr_atr("sexKey") == "Female")
    {
        if (type == "shield")
        {
            sprite_set_offset(charleft_sprite, 
                sprite_get_xoffset(__asset_get_index(scr_atr("BodySprite"))) + 1, 
                sprite_get_yoffset(__asset_get_index(scr_atr("BodySprite"))) + 1);
        }
    }
}
```

## 功能说明

此脚本在左手装备动画结束时触发（Other Event 16），主要作用：

- 针对 `children` 对象执行
- 检查角色性别是否为女性 (`sexKey == "Female"`)
- 如果装备类型是盾牌 (`type == "shield"`)
- 调整左手精灵的偏移量：
  - X 偏移 = 身体精灵的 X 偏移 + 1
  - Y 偏移 = 身体精灵的 Y 偏移 + 1

## 用途
修正女性角色装备盾牌时的精灵位置偏移。
