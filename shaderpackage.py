"""Basic Oblivion shader package reading/writing

   Most of this was from reading OBMM code, so for example where it's unsure if the
   official format is a uint32 vs an int32, it's because OBMM uses int32 but the value
   itself would make more sense as a uint32.

   Values are Little Endian byte-order

   Format:
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

   Notes/Q's:
    - Does the game engine care what the timestamp of the SDP is?
    - Does the game engine do any error checking to verify `count`, `data_size`, etc are accurate?
    - If not: does the game engine crash if bad values are fed to it here?
    - Is there a shader decompiler we can run these through to get back to the code (even without variable names?)
      A: disassembler at least - https://github.com/aizvorski/dx-shader-decompiler/
    - What does the game engine do if two of the same filename are in the same shader package?
    - What encoding does the game engine assume for the filename entries?
"""
import struct
import os


__all__ = [
    'Shader',
    'ShaderPackage',
]


# Helper functions for reading/writing data
def _generate_readwrite(format, single=False):
    compiled = struct.Struct(format)
    size = compiled.size
    packer = compiled.pack
    unpacker = compiled.unpack
    if single:
        # Single variable packer/unpacker
        def read(input_stream):
            return unpacker(input_stream.read(size))[0]
        def write(output_stream, value):
            return output_stream.write(packer(value))
    else:
        def read(input_stream):
            return unpacker(input_stream.read(size))
        def write(output_stream, *values):
            return output_stream.write(packer(*values))
    return read, write

read_int32, write_int32 = _generate_readwrite('<i', True)
read_uint32, write_uint32 = _generate_readwrite('<I', True)


def write_name(output_stream, name, encoding='utf8', size=0x100):
    """Write filename, padded with nulls, for a total of 0x100 bytes."""
    name = name.encode(encoding)
    assert len(name) <= size
    buffer = bytearray(size)
    buffer[0:len(name)] = name
    output_stream.write(buffer)


class Shader:
    """Represents a single shader."""
    def __init__(self, filename, shader_data):
        self.filename = filename
        self.shader_data = shader_data

    def __repr__(self):
        return f"<Shader '{self.filename}' - {len(self.shader_data)}>"

    @classmethod
    def from_stream(cls, input_stream):
        """Read in shader information from an already open shader package,
           with the file read position at the beginning of the shader
           entry you want to read."""
        name = input_stream.read(0x100).strip(b'\x00').decode('utf8')
        size = read_int32(input_stream)
        shader_data = input_stream.read(size)
        return cls(name, shader_data)

    @classmethod
    def from_object_file(cls, filename):
        """Read in shader information from vertex/pixel shader object file (.vso/.pso)"""
        with open(filename, 'rb') as input_stream:
            shader_data = input_stream.read()
            return cls(filename, shader_data)

    def write_object_file(self, directory, filename=None):
        """Write the shader out as a vertex/pixel shader object file (.vso/.pso),
           in the directory `directory`. If `filename` is not specified, use the
           filename that was attached to this shader at creation (read from file,
           read from package)."""
        if filename is None:
            filename = self.filename
        filename = os.path.join(directory, filename)
        with open(filename, 'wb') as output_stream:
            output_stream.write(self.shader_data)

    def write_stream(self, output_stream):
        """Write shader information to an already open shader package,
           with the file write position where the shader entry should
           be written."""
        write_name(output_stream, self.filename)
        write_int32(output_stream, len(self.shader_data))
        output_stream.write(self.shader_data)


class ShaderPackage(list):
    """Basically a thin wrapper around a list of `Shader` objects."""
    MAGIC = 100

    @classmethod
    def from_shaderpackage(cls, filename):
        """Reads shader data from a shader package, with almost no error
           checking of claimed sizes."""
        with open(filename, 'rb') as input_stream:
            magic = read_int32(input_stream)
            assert magic == cls.MAGIC
            count = read_int32(input_stream)
            data_size = read_int32(input_stream)
            return cls(Shader.from_stream(input_stream) for _ in range(count))

    @classmethod
    def from_directory(cls, directory):
        """Read all shader object files from a directory."""
        # Changing working directory is hacky, probably need to decouple
        # internal storage of the filename from the actual path string
        ret = cls()
        cwd = os.getcwd()
        try:
            os.chdir(directory)
            for filename in os.listdir('.'):
                ext = os.path.splitext(filename)[1].lower()
                if ext in ('.vso', '.pso'):
                    ret.append(Shader.from_object_file(filename))
            return ret
        finally:
            os.chdir(cwd)

    def write_file(self, filename):
        """Save the whole shader package to file."""
        with open(filename, 'wb') as output_stream:
            # Write the header (mostly)
            write_int32(output_stream, self.MAGIC)
            write_int32(output_stream, len(self))
            # Write the size info later
            size_offset = output_stream.tell()
            write_int32(output_stream, 0)
            # Write the shader array
            for shader in self:
                shader.write_stream(output_stream)
            # Go back and fill in the final size
            size = output_stream.tell() - 12 # Don't include header size
            output_stream.seek(size_offset, os.SEEK_SET)
            write_int32(output_stream, size)

    def unpack(self, directory):
        """Save the individual shaders in the shader package to directory."""
        if not os.path.exists(directory):
            os.makedirs(directory)
        for shader in self:
            shader.write_object_file(directory)
