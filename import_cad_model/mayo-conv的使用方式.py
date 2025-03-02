import subprocess

exe = r"F:\Downloads\开源cad模型查看转换软件Mayo-0.9.0-win64-binaries\Mayo-0.9.0-win64-binaries\mayo-conv.exe"
options = r"D:\OP-1.stp"
orig = ['--export', r"D:\OP-1.gltf"]

# 构建命令列表
cmd = [exe, options] + orig

# 打印命令列表以便调试
print(cmd)

“如果路径里有空格就整个路径用双引号包裹
mayo-conv.exe --use-settings "C:\Users\CP\AppData\Roaming\Blender Foundation\Blender\Addons_CP\addons\import_cad_model\mayo-gui.ini" X:\1111\2025年后笔记本往台式机转存文件\dji-fpv-o3-camera-unit-1.snapshot.6\DJIO3CAM.step --export D:\111111111111111.obj

mayo-conv.exe X:\1111\2025年后笔记本往台式机转存文件\dji-fpv-o3-camera-unit-1.snapshot.6\DJIO3CAM.step --export D:\111111111111111.obj

## 运行命令
subprocess.run(cmd)

F:\Downloads\开源cad模型查看转换软件Mayo-0.9.0-win64-binaries\Mayo-0.9.0-win64-binaries\mayo-conv.exe --use-settings F:\Downloads\开源cad模型查看转换软件Mayo-0.9.0-win64-binaries\Mayo-0.9.0-win64-binaries\mayo-gui.ini D:\OP-1.stp --export D:\OP-1.gltf
##mayo-conv.exe如何实用软件设置里的网格配置 https://github.com/fougue/mayo/issues/276
mayo-conv --use-settings D:\data\mayo-gui.ini inputfile.step --export outputfile.wrl

mayo-conv.exe D:\白色半透明塑料副本.stp --export D:\OP-1.gltf --no-progress
'''--no-progress可以返回info
F:\Downloads\开源cad模型查看转换软件Mayo-0.9.0-win64-binaries\Mayo-0.9.0-win64-binaries>mayo-conv.exe D:\白色半透明塑料副本.stp --export D:\OP-1.gltf --no-progress
INFO: "Importing..."
CRITICAL: "Error during import of 'D:\\白色半透明塑料副本.stp'\nFile read problem "

成功就是
INFO: "Importing..."
INFO: "Imported"
INFO: "Exporting OP-1.gltf..."
INFO: "Exported OP-1.gltf"
'''


mayo-conv.exe --system-info
'''
F:\Downloads\开源cad模型查看转换软件Mayo-0.9.0-win64-binaries\Mayo-0.9.0-win64-binaries>mayo-conv.exe --system-info

Mayo: v0.9.0  commit:614755f  revnum:1366  64bit

OS: Windows 10 Version 2009 [winnt version 10.0.22631]
Current CPU Architecture: x86_64

Qt 5.15.2 (x86_64-little_endian-llp64 shared (dynamic) release build; by MSVC 2019)

OpenCascade: 7.8.0 (build)

Assimp: 5.4.3 rev:0 branch:? flags:shared|single-threaded

Import(read) formats:
    DXF STEP IGES OCCBREP STL GLTF OBJ VRML OFF PLY AMF 3DS 3MF COLLADA FBX X3D Blender X
Export(write) formats:
    STEP IGES OCCBREP STL VRML GLTF OBJ OFF PLY Image
'''


F:\Downloads\开源cad模型查看转换软件Mayo-0.9.0-win64-binaries\Mayo-0.9.0-win64-binaries>mayo-conv.exe --help
Usage: mayo-conv.exe [options] [files...]
mayo-conv the opensource CAD converter

Options:
  -?, -h, --help                         Display help on commandline options
  -v, --version                          Display version information
  -u, --use-settings <filepath>          Use settings file(INI format) for the
                                         conversion. When this option isn't
                                         specified then cached settings are used
  -c, --cache-settings                   Cache settings file provided with
                                         --use-settings for further use
  -w, --write-settings-cache <filepath>  Write settings cache to an output
                                         file(INI format)
  -e, --export <filepath>                Export opened files into an output
                                         file, can be repeated for different
                                         formats(eg. -e file.stp -e file.igs...)
  --log-file <filepath>                  Writes log messages into output file
  --debug-logs                           Don't filter out debug log messages in
                                         release build
  --no-progress                          Disable progress reporting in console
                                         output
  --system-info                          Show detailed system information and
                                         quit

Arguments:
  files                                  Files to open(import)
