## Basic Oblivion shader package reading/writing

Most of this was from reading OBMM code, so for example where it's unsure if the official format is a `uint32` vs an `int32`, it's because OBMM uses int32 but the value itself would make more sense as a `uint32`.

# Format: Values are Little Endian byte-order

```
HEADER:
    4 bytes: `magic` - 64 00 00 00 (hex), or 100 in decimal
    (u?)int32: `count` - number of shaders in this shader package
    (u?)int32: `data_size` - total size in bytes of the shader data (so file size - 12 bytes for the header)
ARRAY: `count` entries, packed (no padding bytes)
    ENTRY:
        0x100 bytes: `name` - name of the shader file name (ex: SLS1000.vso)
        (u?)int32: `shader_size` - size of the shader data
        `shader_size` bytes: `compiled_shader` - raw binary data of the compiled shader.  This is exactly
                                                 what would be in the file if it were a loose file.
```

## Notes/Q's
 - Does the game engine care what the timestamp of the SDP is?
 - Does the game engine do any error checking to verify `count`, `data_size`, etc are accurate?
 - If not: does the game engine crash if bad values are fed to it here?
 - Is there a shader decompiler we can run these through to get back to the code (even without variable names?)
   **A: disassembler at least - https://github.com/aizvorski/dx-shader-decompiler/**
 - What does the game engine do if two of the same filename are in the same shader package?
 - What encoding does the game engine assume for the filename entries?
