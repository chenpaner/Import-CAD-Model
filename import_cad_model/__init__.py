
bl_info = {
    "name" : "Import CAD Model",
    "author" : "CP-Design", 
    "description" : "This addon lets you import CAD Model(stp/iges) files in Blender 4.0+",
    "blender" : (4, 0, 0),
    "version" : (1, 0, 0),
    "location" : "File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop",
    "warning" : "Only Blender 4.0+ versions and Windows are supported",
    "doc_url": "", 
    "tracker_url": "", 
    "category" : "Import" 
}

import bpy
import os
import re
import sys
import subprocess
import threading
import queue
from bpy.props import (StringProperty,
                       BoolProperty,
                       EnumProperty,
                       IntProperty,
                       FloatProperty,
                       CollectionProperty)
from bpy_extras.io_utils import ImportHelper, poll_file_object_drop
import time
import configparser
from bpy.app.handlers import persistent
from bpy.app.translations import pgettext_iface as _

def get_ini_directory():
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(plugin_dir, "mayo-gui.ini")

def update_inifile(self, context):
    ini_path = get_ini_directory()
    if not os.path.isfile(ini_path):
        print(_('No found the mayo-gui.ini file in plugin directory!'))
        return

    config = configparser.ConfigParser()
    config.read(ini_path)

    # 读取ini_path这个文件，找到这个文件里以meshingQuality=开头的这行，将这行改为meshingQuality=self.mesh_quality,然后保存文件

    # 检查 meshing section 是否存在，并且 meshingQuality 是否在其中
    if 'meshing' in config and 'meshingQuality' in config['meshing']:
        # 如果存在，则更新 meshingQuality 的值
        config['meshing']['meshingQuality'] = self.mesh_quality
    else:
        # 如果不存在，则添加 meshingQuality 到 meshing section
        if 'meshing' not in config:
            config['meshing'] = {}
        config['meshing']['meshingQuality'] = self.mesh_quality

    with open(ini_path, 'w') as configfile:
        config.write(configfile)

#####每次操作前都要把语言设置为en，不然可能返回的内容是中文
def set_inifile_language():
    ini_path = get_ini_directory()
    if not os.path.isfile(ini_path):
        print(_('No found the mayo-gui.ini file in plugin directory!'))
        return

    config = configparser.ConfigParser()
    config.read(ini_path)
    if 'application' in config and 'language' in config['application']:
        config['application']['language'] = "en"
    else:
        if 'application' not in config:
            config['application'] = {}
        config['application']['language'] = "en"

    with open(ini_path, 'w') as configfile:
        config.write(configfile)

def get_pre():
    return bpy.context.preferences.addons[__package__].preferences

@persistent
def load_set_show_import_plane_handler(dummy):
    try:
        get_pre().show_import_plane = True
    except:
        pass

class MayoConvPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_import_plane: bpy.props.BoolProperty(
        name=_('Show Options Panel Before Import'),
        description=_('Display this panel before each import.\nAuto reset on file load/creat new file.\nCan be re-enabled in the plugin settings.'),
        default=True
    )

    exe_path: StringProperty(
        name=_("mayo-conv.exe Path"),  # 🌐
        subtype='FILE_PATH',
        default=_("..../mayo-conv.exe (Not mayo.exe)"),  # 🌐
        description=_("Path to mayo-conv.exe executable")  # 🌐
    )

    geshi: bpy.props.EnumProperty(
        name=_('Convert Target Format'),  # 🌐
        description='Mayo export format and Blender improt Format',
        items=[
            ('.gltf', '.gltf', _('GLTF: Import with empty object hierarchy'), 0, 0),  # 🌐
            ('.obj', '.obj', _('OBJ: Import with collection hierarchy'), 0, 1)],  # 🌐
        default='.obj',
        options={'HIDDEN'}
    )

    ###其实这个导入ini可以直接设置,这些属性直接可以update更新插件里的ini文件
    # ini_path: StringProperty(
    #     name="you mesh set.ini Path",
    #     subtype='FILE_PATH',
    #     default=r"F:\Downloads\开源cad模型查看转换软件Mayo-0.9.0-win64-binaries\Mayo-0.9.0-win64-binaries\mayo-gui.ini",
    #     description="Path to mayo-meshing set"
    # )

    mesh_quality: EnumProperty(
        name=_('Mesh Quality'),  # 🌐
        description=_('Controls CAD model to mesh conversion precision'),  # 🌐
        items=[
            ('VeryCoarse', _('Very Coarse'), _('Fastest conversion with low detail'), 0, 0),  # 🌐
            ('Coarse', _('Coarse'), _('Coarse quality'), 0, 1),  # 🌐
            ('Normal', _('Normal'), _('Standard quality'), 0, 2),  # 🌐
            ('Precise', _('Precise'), _('High precision'), 0, 3),  # 🌐
            ('VeryPrecise', _('Very Precise'), _('Highest precision'), 0, 4)],  # 🌐
        default='Normal',
        options={'HIDDEN'},
        update=update_inifile
    )
    
    # global_scale : FloatProperty(
    # name='Scale', 
    # description='Value by which to enlarge or shrink the objects with respect to the world origin', 
    # default=1.0, min=9.999999747378752e-05, max=10000.0)

    global_scale:EnumProperty(
        items=[
        # ("1000", "1000.0", "Scale by 1000.0"),
        ("100", "100.0", "Scale by 100.0"),
        ("10", "10.0", "Scale by 10.0"),
        ("1", "1.0", "Scale by 1.0"),
        ("0.1", "0.1", "Scale by 0.1"),
        ("0.01", "0.01", "Scale by 0.01"),
        ("0.001", "0.001", "Scale by 0.001"),
        ("0.0001", "0.0001", "Scale by 0.0001"),
        ],
        name=_("Scale Factor"),  # 🌐
        description=_("Scaling factor for each object in OBJ format,\nScaling factor of the parent empty object in GLTF format"),  # 🌐
        default="1"
    )

    forward_axis : EnumProperty(
        name='Forward Axis', description='', 
        items=[
            ('X', 'X', 'Positive X axis'), 
            ('Y', 'Y', 'Positive Y axis'), 
            ('Z', 'Z', 'Positive Z axis'), 
            ('NEGATIVE_X', '-X', 'Negative X axis'), 
            ('NEGATIVE_Y', '-Y', 'Negative Y axis'), 
            ('NEGATIVE_Z', '-Z', 'Negative Z axis')
            ], 
        default='NEGATIVE_Z'
        )
    up_axis : EnumProperty(
        name='Up Axis', description='', 
        items=[
            ('X', 'X', 'Positive X axis'), 
            ('Y', 'Y', 'Positive Y axis'), 
            ('Z', 'Z', 'Positive Z axis'), 
            ('NEGATIVE_X', '-X', 'Negative X axis'), 
            ('NEGATIVE_Y', '-Y', 'Negative Y axis'), 
            ('NEGATIVE_Z', '-Z', 'Negative Z axis')
            ], 
        default='Y'
        )



    del_gltf: BoolProperty(
        name=_('Del Mesh File After Imported'),  # 🌐
        description=_('Automatically remove converted files post-import'),  # 🌐
        default=True,
        options={'HIDDEN'}
    )
    clean_mat: BoolProperty(
        name=_('Clean Duplicate Materials'),  # 🌐
        description=_('Remove import-duplicate Materials with .001 suffixes '),  # 🌐
        default=True,
        options={'HIDDEN'}
    )

    def draw(self, context):
        layout = self.layout
        row = layout.box().column(align=True)
        row.alert = not os.path.exists(self.exe_path)#True
        row.scale_x = 1.5
        row.prop(self, "exe_path")

        # row = layout.row(align=True)
        # row.alert = not os.path.exists(self.ini_path)#True
        # row.prop(self, "ini_path")

        # layout.prop(self, "global_scale")
        # layout.prop(self, "mesh_quality")

        row = layout.box().column(align=True)
        row.prop(self, "del_gltf")
        row.prop(self, "clean_mat")

        row = layout.box().column(align=True)
        row.label(text=_("Settings are temporary - will reset on Blender restart/new file"), icon="QUESTION")
        row.prop(self, "show_import_plane")

        
        # layout.label(text='导入进程中不要切换控制台窗口为活动窗口！',icon="QUESTION")
        row = layout.box().column(align=True)
        # row.label(text='重要提示！',icon="QUESTION")
        # row.label(text='1.这个插件是通过第三方开源免费软件Mayo将CAD模型(.step/.stp/.iges/.igs)转换为用户直到的网格格式(obj/gltf),然后导入到Blender')
        # row.label(text='2.但你的CAD模型可能从任何你实际工作的软件里导出的,这些格式有很多不确定的参数,所有如果导入的网格和你的CAD模型不一致')
        # row.label(text='  你需要手动去Mayo里导入你的CAD模型，通过在"Tools">"Options"调整参数，然后重新在Mayo里导入CAD模型,')
        # row.label(text='  如果设置满足你的需求后,在Options面板的底部 Click Exchange->Save as... ,然后覆盖掉插件文件里的mayo-gui.ini文件')
        # row.label(text='3.mayo-gui.ini文件里的meshingQuality选项可通过导入面板里的选项自动设置')
        # row.label(text='4.How Use:File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or 直接拖动模型到3D窗口里')
        row.label(text='Critical Usage Notes:', icon="QUESTION")
        row.label(text='1. This plugin uses the open-source Mayo to transform CAD models into mesh formats (obj/gltf) for Blender import')
        row.label(text='2. CAD models may contain format-specific parameters from your CAD software. If imported mesh mismatches:')
        row.label(text='   a) Start mayo.exe, Adjust parameters under "Tools > Options"')
        row.label(text='   b) Manually import the CAD file in Mayo')
        row.label(text='   c) After optimization, click "Exchange > Save as..." at bottom of Options panel')
        row.label(text='   d) Overwrite the mayo-gui.ini file in plugin directory')
        row.label(text='3. The meshingQuality parameter in the mayo-gui.ini file can be manually set in the import panel.')
        row.label(text='4. Usage: File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop to 3D Viewport')


        layout = self.layout 
        box_0CD4E = layout.box()
        box_0CD4E.scale_y = 0.7
        box_0CD4E.label(text='Sell a plugin ^_~', icon='RNA')
        box_0CD4E.label(text='A plug-in that can be converted between the collection and the empty object hierarchy!', icon='FUND')
        box_0CD4E.label(text='Move the empty at the center of the sub-level objects instead of the center of the world coordinates!', icon='FUND')
        
        row_D6666 = box_0CD4E.row(heading='', align=True)
        row_D6666.scale_y = 1.5
        op = row_D6666.operator('wm.url_open', text='Empty & Collection Switcher', icon="SCRIPTPLUGINS", emboss=True, depress=False)
        op.url = 'https://blendermarket.com/products/empty--collection-switcher'
        
'''
class IMPORT_OT_STEPtoGLTF(bpy.types.Operator, ImportHelper):
    """Convert STEP to glTF and import"""
    bl_idname = "import_scene.step_to_gltf"
    bl_label = "Import STEP"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".step;.stp"
    filter_glob: StringProperty(
        default="*.step;*.stp",
        options={'HIDDEN'},
    )
    files: CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    geshi: bpy.props.EnumProperty(name='Format', description='', items=[
        ('.gltf', 'Gltf', 'GLTF导入慢，层级结构为空物体的子级方式', 0, 0), 
        ('.obj', 'Obj', 'OBJ速度快，层级结构为集合方式', 0, 1)],
        default='.gltf',options={'HIDDEN'},)
    del_gltf:BoolProperty(name='导入后删除生成的GLTF/obj文件',description='',default=True,options={'HIDDEN'},)

    global_scale: FloatProperty(
        name='Scale',
        description='Scale',
        default=1.0,
        min=0.0001,max=10000,options={'HIDDEN'},
    )

    def draw(self, context):
        operator = self
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(self, 'geshi')
        layout.prop(self, 'del_gltf')
        layout.prop(self, 'global_scale')

    def invoke(self, context, event):
        if len(self.files )>1:
            self.report({'ERROR'}, "Just one stp import!")
            return {'CANCELLED'}
        return ImportHelper.invoke_popup(self, context)

    def execute(self, context):
        # 获取首选项设置
        
        # 验证路径
        if not os.path.exists(get_pre().exe_path):
            self.report({'ERROR'}, "mayo-conv.exe路径无效！")
            return {'CANCELLED'}
    
        # 验证路径
        if not os.path.exists(get_pre().ini_path):
            self.report({'ERROR'}, "ini_path路径无效！")
            return {'CANCELLED'}

        # 准备路径
        input_path = os.path.abspath(self.filepath)
        output_dir = os.path.dirname(input_path)
        output_name = os.path.splitext(os.path.basename(input_path))[0]
        gltf_path = os.path.join(output_dir, output_name + self.geshi)

        #??是否应该在转换gltf前先检查是否已经有这个gltf文件，避免在cmd运行时就直接导入这个久的文件？？
        # 在构建cmd之前添加
        if os.path.exists(gltf_path):
            try:
                os.remove(gltf_path)
                # self.report({'INFO'}, "已清理旧版本文件: " + gltf_path)
            except Exception as e:
                self.report({'WARNING'}, "无法删除旧文件: " + str(e))

        # 构建命令
        exe = get_pre().exe_path
        ini = get_pre().ini_path
        # useini = ['--use-settings',ini]
        options = input_path
        # orig = ['--export', gltf_path]

        # 构建命令列表
        # cmd = [exe,'--use-settings',ini,options] + orig
        # 修改cmd构建部分
        cmd = [
            exe,
            '--use-settings', ini,
            input_path,  # 输入文件
            '--export', gltf_path   # 输出文件（直接作为参数）
        ]


        # 打印命令列表以便调试
        print(cmd)
        self.report({'INFO'}, "转换文件中......")
        try:
            # 运行转换命令
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 检查输出是否包含成功信息
            if "100% Exported" not in result.stdout:
                self.report({'ERROR'}, "转换失败，未生成有效输出")
                return {'CANCELLED'}

            ##？这个导入一定是在上面准换文件完成后才执行导入么？能否在上面转换的过程中在ui里显示进度
            # 导入生成的glTF文件
            self.report({'INFO'}, "转换完成，正在导入中...")
            if os.path.exists(gltf_path):
                if self.geshi=='.gltf':
                    bpy.ops.import_scene.gltf(filepath=gltf_path,merge_vertices=True)
                    #这里添加一个缩放将空物体缩放
                else:
                    #global_scale （float in [0.0001， 10000]， （可选）） – 比例
                    # use_split_objects （boolean， （optional）） – 按 Object 分割，将每个 OBJ 'o' 作为单独的 object 导入
                    # use_split_groups （boolean， （optional）） – 按组拆分，将每个 OBJ 'g' 作为单独的 OBJ等导入
                    # validate_meshes （boolean， （optional）） – 验证网格，确保数据有效（禁用时，可能会导入数据，从而导致显示或编辑崩溃）
                    # collection_separator （string， （optional， never None）） – 路径分隔符，用于将对象名称分隔为层次结构的字符
                    bpy.ops.wm.obj_import(filepath=gltf_path,global_scale=get_pre().global_scale,use_split_objects=True,use_split_groups=True,collection_separator='/')
                self.report({'INFO'}, "成功导入: " + gltf_path)
                if get_pre().del_gltf:
                    os.remove(gltf_path)
            else:
                self.report({'ERROR'}, "输出文件未生成: " + gltf_path)
                return {'CANCELLED'}

        except subprocess.CalledProcessError as e:
            self.report({'ERROR'}, f"转换失败: {e.stderr}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}
'''

'''
#使用多线程,速度没加快，状态栏还不显示
class IMPORT_OT_STEPtoGLTF(bpy.types.Operator, ImportHelper):
    """Convert STEP to glTF and import"""
    bl_idname = "import_scene.step_to_gltf"
    bl_label = "Import STEP/IGES"
    # bl_options = {'REGISTER', 'UNDO'}

    # filename_ext = ".step;.stp;.iges;.igs"
    filter_glob: StringProperty(
        default="*.step;*.stp;*.iges;*.igs",
        options={'HIDDEN'},
    )

    directory: bpy.props.StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE', 'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'SKIP_SAVE', 'HIDDEN'})
    
    

    _timer = None
    _process = None

    @classmethod
    def poll(cls, context):
        return (context.area and context.area.type == "VIEW_3D")

    def draw(self, context):
        operator = self
        layout = self.layout

        # layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        pre=get_pre()
        layout.prop(pre, 'geshi')
        
        layout.prop(pre, 'global_scale')

        layout.prop(pre, 'mesh_quality')

        layout.prop(pre, 'del_gltf')
        layout.prop(pre, 'clean_mat')

        layout.prop(pre, "show_import_plane")

    def invoke(self, context, event):
        self.geshi=get_pre().geshi
        self.start_time = time.time()
        
        if len(self.files)>1:
            self.report({'ERROR'}, "Just one stp import!")
            return {'CANCELLED'}

        if not get_pre().show_import_plane:
            return self.execute(context)
        ## 使用 ImportHelper 的 invoke_popup() 函数来处理调用，以便这个操作符的属性
        # 在弹出窗口中显示。这允许用户在操作员上配置额外的设置，比如
        # set_label 属性。考虑在操作符中添加一个 draw() 方法，以便布局。
        # 在用户界面中适当设置属性。
        #
        # 如果没有提供文件路径信息，文件选择窗口将被调用。
        
        return self.invoke_popup(context)

    def modal(self, context, event):
        if event.type in {'ESC'}:
            bpy.context.workspace.status_text_set(None)
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':               
            if not self.thread.is_alive():
                self.report({'INFO'}, "转换完成，正在导入中...")
                bpy.context.workspace.status_text_set(f"转换完成，正在导入中...")
                # 结束计时器
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
                
                if not self.result_queue.empty():
                    success, result = self.result_queue.get()
                    if success:
                        self.report({'INFO'}, f"Subprocess completed successfully:\n{result}")
                    else:
                        self.report({'ERROR'}, f"Subprocess failed:\n{result}")
                
                # # 增强结果验证
                # success_keywords = ["100% exported", "100% Exported", "completed"]
                # if not any(key in result_output.lower() for key in success_keywords):
                #     self.report({'ERROR'}, f"转换失败: {result_output[:200]}...")
                #     return {'CANCELLED'}

                # 准备文件路径
                output_path = os.path.join(
                    os.path.dirname(self.filepath),
                    os.path.splitext(os.path.basename(self.filepath))[0] + self.geshi
                )

                # 增强文件检查
                if not os.path.exists(output_path):
                    self.report({'ERROR'}, f"输出文件不存在: {output_path}")
                    return {'CANCELLED'}

                # 确保文件可读
                try:
                    with open(output_path, 'rb') as f_test:
                        pass
                except IOError as e:
                    self.report({'ERROR'}, f"文件访问失败: {str(e)}")
                    return {'CANCELLED'}

                # 取消所有物体的选择
                for obj in bpy.context.selected_objects:
                    obj.select_set(False)

                # 执行导入操作
                scale_factor = float(get_pre().global_scale)
                try:
                    if self.geshi == '.gltf':
                        bpy.ops.import_scene.gltf(
                            filepath=output_path,
                            merge_vertices=True
                        )
                    elif self.geshi == '.obj':
                        # 使用新版本OBJ导入器
                        bpy.ops.wm.obj_import(
                            filepath=output_path,
                            global_scale=scale_factor,
                            use_split_objects=True,
                            use_split_groups=True,
                            collection_separator='/'
                        )
                    # elif self.geshi == '.stl':  # 添加STL支持
                    #     bpy.ops.import_mesh.stl(
                    #         filepath=output_path,
                    #         global_scale=get_pre().global_scale
                    #     )
                except Exception as import_error:
                    self.report({'ERROR'}, f"导入失败: {str(import_error)}")
                    return {'CANCELLED'}

                # 清理生成文件
                if get_pre().del_gltf:
                    try:
                        os.remove(output_path)
                        # 同时清理关联文件（针对glTF）
                        if self.geshi == '.obj':
                            bin_path = os.path.splitext(output_path)[0] + ".mtl"
                            if os.path.exists(bin_path):
                                os.remove(bin_path)
                    except Exception as e:
                        self.report({'WARNING'}, f"文件清理失败: {str(e)}")

               
                # 处理新导入的物体
                new_objects = [obj for obj in bpy.context.view_layer.objects if obj not in self.initial_objects]

                new_mats = [mat for mat in bpy.data.materials if mat not in self.before_import_mat]
                for mat in new_mats:
                    current_color = mat.diffuse_color
                    mat.diffuse_color = (current_color[0], current_color[1], current_color[2], 1)

                # 正则表达式匹配 . 后面跟着数字的模式
                suffix_pattern = re.compile(r'\.\d+$')
                empty_object = None
                for obj in new_objects:
                    if obj.type == 'EMPTY':
                        empty_object = obj
                        if get_pre().clean_mat:
                            break
                    if get_pre().clean_mat and obj.type == 'MESH' and obj.data:
                        if obj.material_slots:
                            for solt in obj.material_slots:
                                if solt.material and solt.material in new_mats:
                                    newmat=solt.material
                                    match = suffix_pattern.search(solt.material.name)
                                    if match:
                                        # 删除后缀
                                        base_name = suffix_pattern.sub('', solt.material.name)
                                        oldmat = bpy.data.materials.get(base_name)
                                        if oldmat:
                                            solt.material=oldmat
                                            if newmat.users == 0:
                                                bpy.data.materials.remove(newmat)


                if empty_object and self.geshi == '.gltf':
                    # 设置空物体为活动物体并选中
                    bpy.context.view_layer.objects.active = empty_object
                    empty_object.select_set(True)
                    empty_object.empty_display_size = 1.0
                    # empty_object.empty_display_type = 'CUBE'
                    empty_object.show_name = True
                    empty_object.show_in_front = True

                    # 缩放空物体
                    empty_object.scale = (0.1/scale_factor, 0.1/scale_factor, 0.1/scale_factor)
                # else:
                #     # 取消所有物体的选择
                #     for obj in new_objects:
                #         obj.select_set(False)

                try:
                    if context.space_data.region_3d.view_perspective != 'CAMERA':
                        bpy.ops.view3d.view_selected(use_all_regions=False)
                except:
                    pass
                elapsed_s = "{:.2f}s".format(time.time() - self.start_time)
                bpy.context.workspace.status_text_set(None)
                self.report({'INFO'}, f"导入流程完成(stp import finished in {elapsed_s})")
                return {'FINISHED'}
            else:
                # self.report({'INFO'}, "stp转换文件中......['ESC'停止导入]")
                # 显示实时进度（示例）
                try:
                    success, result = self.result_queue.get()
                    print(f"Process Output: {success}/////{result}")
                    bpy.context.workspace.status_text_set(f"['ESC'停止导入] mayo {result}")
                    for area in context.screen.areas:
                        for region in area.regions:
                            if region.type == 'STATUSBAR':
                                region.tag_redraw()
                except:
                    pass

        if event.value == "PRESS" or event.type in {"MOUSEMOVE"}:
            return {"RUNNING_MODAL"}

        # return {"RUNNING_MODAL"}
        return {'PASS_THROUGH'}#这个可以让鼠标还能控制

    def execute(self, context):
        # 路径验证增强
        if not os.path.isfile(get_pre().exe_path):
            self.report({'ERROR'}, "mayo-conv.exe路径无效或不是文件！")
            return {'CANCELLED'}

        ini_path = get_ini_directory()
        if not os.path.isfile(ini_path):
            self.report({'ERROR'}, "ini文件路径无效或不是文件！")
            return {'CANCELLED'}

        # 构建输出路径
        input_path = os.path.abspath(self.filepath)
        output_dir = os.path.dirname(input_path)
        output_base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, output_base + self.geshi)

        # 清理旧文件增强
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                self.report({'WARNING'}, f"旧文件清理失败: {str(e)}")

        # 记录初始对象
        self.initial_objects = list(bpy.context.view_layer.objects)
        self.before_import_mat = list(bpy.data.materials)
        # 设置模态计时器

        # 构建正确命令格式
        exe = get_pre().exe_path
        cmd = [
            exe,
            '--use-settings', ini_path,
            input_path,
            '--export', output_path
        ]

        self.result_queue = queue.Queue()
        self.thread = threading.Thread(target=self.run_subprocess, args=(cmd,))
        self.thread.start()
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def run_subprocess(self, cmd):
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                self.result_queue.put((True, stdout))
            else:
                self.result_queue.put((False, stderr))
        except Exception as e:
            self.result_queue.put((False, str(e)))

    def cancel(self, context):
        # 清理资源增强
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except:
                pass
            finally:
                self._process = None
        
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        
        # # 结束进度条
        # if context.window_manager.progress_is_modal():
        #     context.window_manager.progress_end()
        
        # 清理生成文件（即使未完成）
        if hasattr(self, 'del_gltf') and get_pre().del_gltf:
            output_path = os.path.join(
                os.path.dirname(self.filepath),
                os.path.splitext(os.path.basename(self.filepath))[0] + self.geshi
            )
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                    # 清理关联文件
                    if self.geshi == '.obj':
                        bin_path = os.path.splitext(output_path)[0] + ".mtl"
                        if os.path.exists(bin_path):
                            os.remove(bin_path)
            except Exception as e:
                self.report({'WARNING'}, f"中断文件清理失败: {str(e)}")

        self.report({'INFO'}, "操作已取消")


##self._process可参考的官方命令class ASSET_OT_open_containing_blend_file(Operator)

#self._process.stdout.readline() 是阻塞式的，它会等待一行输出直到有数据可读。如果外部程序在完成时没有正确关闭其标准输出流，这可能会导致 poll() 方法无法及时返回。
class IMPORT_OT_STEPtoGLTF(bpy.types.Operator, ImportHelper):
    """Convert STEP to glTF and import"""
    bl_idname = "import_scene.step_to_gltf"
    bl_label = "Import STEP/IGES"
    # bl_options = {'REGISTER', 'UNDO'}

    # filename_ext = ".step;.stp;.iges;.igs"
    filter_glob: StringProperty(
        default="*.step;*.stp;*.iges;*.igs",
        options={'HIDDEN'},
    )

    directory: bpy.props.StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE', 'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'SKIP_SAVE', 'HIDDEN'})
    
    
    def __init__(self):
        self.stop_readpro = False
        self._timer = None
        self._process = None

    # @classmethod
    # def poll(cls, context):
    #     return (context.area and context.area.type == "VIEW_3D")

    def draw(self, context):
        operator = self
        layout = self.layout

        # layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        pre=get_pre()
        if pre.geshi=='.gltf':
            layout.label(text='GLTF导入慢，层级结构为空物体的子级方式',icon="QUESTION")
        else:
            layout.label(text='OBJ速度快，层级结构为集合方式',icon="QUESTION")
        layout.prop(pre, 'geshi')

        if pre.geshi=='.gltf':
            layout.label(text='数字越小模型越大',icon="QUESTION")
        else:
            layout.label(text='数值越小模型越小',icon="QUESTION")
        layout.prop(pre, 'global_scale')

        layout.prop(pre, 'mesh_quality')

        layout.prop(pre, 'del_gltf')
        layout.prop(pre, 'clean_mat')

        layout.prop(pre, "show_import_plane")

    # 自动修改视图的裁切深度值  同时监控self._process有没有可能会中通错误
    def invoke(self, context, event):
        self.geshi=get_pre().geshi
        self.start_time = time.time()
        
        if len(self.files)>1:
            self.report({'ERROR'}, "Just one stp import!")
            return {'CANCELLED'}

        if not get_pre().show_import_plane:
            return self.execute(context)
        ## 使用 ImportHelper 的 invoke_popup() 函数来处理调用，以便这个操作符的属性
        # 在弹出窗口中显示。这允许用户在操作员上配置额外的设置，比如
        # set_label 属性。考虑在操作符中添加一个 draw() 方法，以便布局。
        # 在用户界面中适当设置属性。
        #
        # 如果没有提供文件路径信息，文件选择窗口将被调用。
        
        return self.invoke_popup(context)

    def modal(self, context, event):
        if event.type in {'ESC'}:
            bpy.context.workspace.status_text_set(None)
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if self._process is None:
                self.report({'ERROR'}, "Unable to find any running process")
                self.cancel(context)
                return {'CANCELLED'}

            print(self._process.poll())            
            if self._process.poll() is not None:#用于检查子进程是否已经结束。设置并返回returncode属性。
                # self.report({'INFO'}, "转换完成，正在导入中...")
                print(f"Blender Import....")
                #没用 for area in context.screen.areas:
                #         for region in area.regions:
                #             if region.type == 'STATUSBAR':
                #                 region.tag_redraw()
                # 结束计时器
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
                
                # 获取完整输出
                # stdout, stderr = self._process.communicate()
                # print(stdout, stderr)
                
                
                # # 增强结果验证
                # success_keywords = ["100% exported", "100% Exported", "completed"]
                # if not any(key in result_output.lower() for key in success_keywords):
                #     self.report({'ERROR'}, f"转换失败: {result_output[:200]}...")
                #     return {'CANCELLED'}

                # 准备文件路径
                output_path = os.path.join(
                    os.path.dirname(self.filepath),
                    os.path.splitext(os.path.basename(self.filepath))[0] + self.geshi
                )

                # 增强文件检查
                if not os.path.exists(output_path):
                    self.report({'ERROR'}, f"输出文件不存在: {output_path}")
                    return {'CANCELLED'}

                # 确保文件可读
                try:
                    with open(output_path, 'rb') as f_test:
                        pass
                except IOError as e:
                    self.report({'ERROR'}, f"文件访问失败: {str(e)}")
                    return {'CANCELLED'}

                # # 取消所有物体的选择
                # for obj in bpy.context.selected_objects:
                #     obj.select_set(False)

                # 执行导入操作
                scale_factor = float(get_pre().global_scale)
                try:
                    if self.geshi == '.gltf':
                        bpy.ops.import_scene.gltf(
                            filepath=output_path,
                            merge_vertices=True
                        )
                    elif self.geshi == '.obj':
                        # 使用新版本OBJ导入器
                        bpy.ops.wm.obj_import(
                            filepath=output_path,
                            global_scale=scale_factor,
                            use_split_objects=True,
                            use_split_groups=True,
                            collection_separator='/'
                        )
                    # elif self.geshi == '.stl':  # 添加STL支持
                    #     bpy.ops.import_mesh.stl(
                    #         filepath=output_path,
                    #         global_scale=get_pre().global_scale
                    #     )
                except Exception as import_error:
                    self.report({'ERROR'}, f"导入失败: {str(import_error)}")
                    return {'CANCELLED'}

                # 清理生成文件
                if get_pre().del_gltf:
                    try:
                        os.remove(output_path)
                        # 同时清理关联文件（针对glTF）
                        if self.geshi == '.obj':
                            bin_path = os.path.splitext(output_path)[0] + ".mtl"
                            if os.path.exists(bin_path):
                                os.remove(bin_path)
                    except Exception as e:
                        self.report({'WARNING'}, f"文件清理失败: {str(e)}")

               
                # 处理新导入的物体
                new_objects = [obj for obj in bpy.context.view_layer.objects if obj not in self.initial_objects]

                new_mats = [mat for mat in bpy.data.materials if mat not in self.before_import_mat]
                for mat in new_mats:
                    current_color = mat.diffuse_color
                    mat.diffuse_color = (current_color[0], current_color[1], current_color[2], 1)

                # 正则表达式匹配 . 后面跟着数字的模式
                suffix_pattern = re.compile(r'\.\d+$')
                empty_object = None
                for obj in new_objects:
                    if obj.type == 'EMPTY':
                        empty_object = obj
                        if get_pre().clean_mat:
                            break
                    if get_pre().clean_mat and obj.type == 'MESH' and obj.data:
                        if obj.material_slots:
                            for solt in obj.material_slots:
                                if solt.material and solt.material in new_mats:
                                    newmat=solt.material
                                    match = suffix_pattern.search(solt.material.name)
                                    if match:
                                        # 删除后缀
                                        base_name = suffix_pattern.sub('', solt.material.name)
                                        oldmat = bpy.data.materials.get(base_name)
                                        if oldmat:
                                            solt.material=oldmat
                                            if newmat.users == 0:
                                                bpy.data.materials.remove(newmat)


                if empty_object and self.geshi == '.gltf':
                    # 设置空物体为活动物体并选中
                    bpy.context.view_layer.objects.active = empty_object
                    empty_object.select_set(True)
                    empty_object.empty_display_size = 1.0
                    # empty_object.empty_display_type = 'CUBE'
                    empty_object.show_name = True
                    empty_object.show_in_front = True

                    # 缩放空物体
                    empty_object.scale = (0.1/scale_factor, 0.1/scale_factor, 0.1/scale_factor)
                # else:
                #     # 取消所有物体的选择
                #     for obj in new_objects:
                #         obj.select_set(False)

                try:
                    if context.space_data.region_3d.view_perspective != 'CAMERA':
                        bpy.ops.view3d.view_selected(use_all_regions=False)
                except:
                    pass
                elapsed_s = "{:.2f}s".format(time.time() - self.start_time)
                bpy.context.workspace.status_text_set(None)
                self.report({'INFO'}, f"导入流程完成(Import finished in {elapsed_s})")
                return {'FINISHED'}
            else:

                # self.report({'INFO'}, "stp转换文件中......['ESC'停止导入]")
                # 显示实时进度（示例）
                try:
                    if not self.stop_readpro:
                        # 读取部分输出#self._process.stdout.readline() 是阻塞式的，它会等待一行输出直到有数据可读。如果外部程序在完成时没有正确关闭其标准输出流，这可能会导致 poll() 方法无法及时返回。
                        line = self._process.stdout.readline()
                        if line:
                            if line.strip():
                                print(f"Waiting Convert 3D file: {line.strip()}")
                            if "100% Imported" in line.strip():#有可能stp文件小捕获不到信息，或是改为出现这些都表示成功了'100%',"100% Imported","100% Exported"
                                self.stop_readpro=True
                            else:
                                if line.strip():
                                    text=f"Waiting Mayo Convert 3D file: {line.strip()}"
                                    context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context, text,True))
                                    # bpy.context.workspace.status_text_set(f"['ESC'停止导入] Waiting Mayo {line.strip()}")
                    else:
                        context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context,"转换完成，Blender正在导入中..."))
                        # bpy.context.workspace.status_text_set(f"转换完成，Blender正在导入中...")
                        
                except:
                    pass

        # if event.value == "PRESS" or event.type in {"MOUSEMOVE"}:
        #     return {"RUNNING_MODAL"}

        return {"RUNNING_MODAL"}
        # return {'PASS_THROUGH'}#这个可以让鼠标还能控制


    def execute(self, context):
        # 路径验证增强
        if not os.path.isfile(get_pre().exe_path):
            self.report({'ERROR'}, "mayo-conv.exe路径无效或不是文件！")
            return {'CANCELLED'}

        ini_path = get_ini_directory()
        if not os.path.isfile(ini_path):
            self.report({'ERROR'}, "ini文件路径无效或不是文件！")
            return {'CANCELLED'}

        # 构建输出路径
        input_path = os.path.abspath(self.filepath)
        output_dir = os.path.dirname(input_path)
        output_base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, output_base + self.geshi)

        # 取消所有物体的选择
        for obj in bpy.context.selected_objects:
            obj.select_set(False)

        # 清理旧文件增强
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                self.report({'WARNING'}, f"旧文件清理失败: {str(e)}")

        # 构建正确命令格式
        exe = get_pre().exe_path
        cmd = [
            exe,
            '--use-settings', ini_path,
            input_path,
            '--export', output_path
        ]

        # 调试输出
        # print("执行命令:", ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd))

        # 启动进程（增强Windows支持）
        try:
            self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        except Exception as proc_error:
            self.report({'ERROR'}, f"进程启动失败: {str(proc_error)}")
            return {'CANCELLED'}

        # 记录初始对象
        self.initial_objects = list(bpy.context.view_layer.objects)
        self.before_import_mat = list(bpy.data.materials)
        # 设置模态计时器

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        # 初始化进度条
        # context.window_manager.progress_begin(0, 100)
        
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        # 清理资源增强
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except:
                pass
            finally:
                self._process = None
        
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        
        # # 结束进度条
        # if context.window_manager.progress_is_modal():
        #     context.window_manager.progress_end()
        
        # 清理生成文件（即使未完成）
        if hasattr(self, 'del_gltf') and get_pre().del_gltf:
            output_path = os.path.join(
                os.path.dirname(self.filepath),
                os.path.splitext(os.path.basename(self.filepath))[0] + self.geshi
            )
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                    # 清理关联文件
                    if self.geshi == '.obj':
                        bin_path = os.path.splitext(output_path)[0] + ".mtl"
                        if os.path.exists(bin_path):
                            os.remove(bin_path)
            except Exception as e:
                self.report({'WARNING'}, f"中断文件清理失败: {str(e)}")

        self.report({'INFO'}, "操作已取消")

'''

# 进程输出的读取方式：当前代码中，self._process.stdout.readline() 是阻塞式的，它会等待一行输出直到有数据可读。如果外部程序在完成时没有正确关闭其标准输出流，这可能会导致 poll() 方法无法及时返回。

# 非阻塞式读取：为了确保能够实时检测到进程的状态变化，建议使用非阻塞的方式读取子进程的标准输出。

# 轮询间隔：当前模态处理函数中的计时器间隔为0.1秒，这个时间间隔可能不足以频繁地检查进程状态。可以考虑缩短这个间隔或者增加一些额外的逻辑来更准确地判断进程是否结束。
# 解决方案
# 1. 使用非阻塞式读取
# 可以通过创建一个线程或使用异步 I/O 来实现非阻塞读取。
# 2. 缩短轮询间隔
# 如果你不想引入多线程复杂性，也可以尝试缩短计时器间隔，例如设置为 0.05 秒：

#这个就是方案1，使用非阻塞式读取，通过创建一个线程或使用异步 I/O 来实现非阻塞读取
class IMPORT_OT_STEPtoGLTF(bpy.types.Operator, ImportHelper):
    """Convert STEP to glTF and import"""
    bl_idname = "import_scene.step_to_gltf"
    bl_label = "Import STEP/IGES"

    filter_glob: bpy.props.StringProperty(
        default="*.step;*.stp;*.iges;*.igs",
        options={'HIDDEN'},
    )

    directory: bpy.props.StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE', 'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'SKIP_SAVE', 'HIDDEN'})

    def __init__(self):
        self.stop_readpro = False
        self._timer = None
        self._process = None
        self.output_queue = None
        self.output_thread = None

    def draw(self, context):
        operator = self
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        pre=get_pre()

        t=_("OBJ: Import with collections") if pre.geshi == '.obj' else _("GLTF: Import with empty hierarchy")
        row=layout.row()
        row.alert = True
        row.alignment = 'RIGHT'.upper()#'EXPAND', 'LEFT', 'CENTER', 'RIGHT'
        row.label(text=t, icon="QUESTION")
        layout.prop(pre, 'geshi')

        layout.prop(pre, 'mesh_quality')

        if bpy.app.version >= (4, 2):
            layout.separator(type="LINE")  
        else:
            layout.separator()

        row=layout.row()
        row.alert = True
        row.alignment = 'RIGHT'.upper()#'EXPAND', 'LEFT', 'CENTER', 'RIGHT'
        row.label(text=_("Lower values = Smaller model" if pre.geshi == '.obj' else "Lower values = Larger model"),icon="QUESTION")
        layout.prop(pre, 'global_scale')
        if pre.geshi == '.obj':
            layout.prop(pre, 'forward_axis')
            layout.prop(pre, 'up_axis')

        if bpy.app.version >= (4, 2):
            layout.separator(type="LINE")  
        else:
            layout.separator()
        

        layout.prop(pre, 'del_gltf')
        layout.prop(pre, 'clean_mat')

        layout.prop(pre, "show_import_plane")

    def invoke(self, context, event):
        self.geshi = get_pre().geshi
        self.start_time = time.time()
        try:
            context.space_data.clip_start=0.001
            context.space_data.clip_end = 100000
        except:
            pass

        if len(self.files) > 1:
            self.report({'ERROR'}, _("Single file import only"))
            return {'CANCELLED'}

        if not get_pre().show_import_plane:
            return self.execute(context)
        return self.invoke_popup(context)

    def modal(self, context, event):
        if event.type in {'ESC'}:
            bpy.context.workspace.status_text_set(None)
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if self._process is None:
                self.report({'ERROR'}, "Unable to find any running process")
                self.cancel(context)
                return {'CANCELLED'}

                        # 检查队列中的输出
            try:
                while True:
                    source, line = self.output_queue.get_nowait()
                    if "Error" in line.strip():
                        self.report({'ERROR'}, _("Mayo Convert CAD model failed: {}").format(line.strip()))
                        bpy.context.workspace.status_text_set(None)
                        self.cancel(context)
                        return {'CANCELLED'}

                    if line.strip(): 
                        text=_("Please wait,Mayo Converting: {}").format(line.strip())
                        print(text)
                        context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context, text,True))
                    if "100% Imported" in line.strip():
                        self.stop_readpro = True
                        break
            except queue.Empty:
                pass

            if self.stop_readpro:
                context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context,_("Converted ,Importing to Blender...")))#转换完成，Blender正在导入中...
            # print(self._process.poll())            
            if self._process.poll() is not None:#用于检查子进程是否已经结束。设置并返回returncode属性。
                # self.report({'INFO'}, "转换完成，正在导入中...")
                print(f"Blender Importing....")
                
                # 结束计时器
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
                
                # 获取完整输出
                # stdout, stderr = self._process.communicate()
                # print(stdout, stderr)
                
                
                # # 增强结果验证
                # success_keywords = ["100% exported", "100% Exported", "completed"]
                # if not any(key in result_output.lower() for key in success_keywords):
                #     self.report({'ERROR'}, f"转换失败: {result_output[:200]}...")
                #     return {'CANCELLED'}

                # 准备文件路径
                output_path = os.path.join(
                    os.path.dirname(self.filepath),
                    os.path.splitext(os.path.basename(self.filepath))[0] + self.geshi
                )

                # 增强文件检查
                if not os.path.exists(output_path):
                    self.report({'ERROR'}, f"Can`t found mesh model: {output_path}")
                    return {'CANCELLED'}

                # 确保文件可读
                try:
                    with open(output_path, 'rb') as f_test:
                        pass
                except IOError as e:
                    self.report({'ERROR'}, f"Can`t read mesh model: {str(e)}")
                    return {'CANCELLED'}

                # # 取消所有物体的选择
                # for obj in bpy.context.selected_objects:
                #     obj.select_set(False)

                # 执行导入操作
                scale_factor = float(get_pre().global_scale)
                try:
                    if self.geshi == '.gltf':
                        bpy.ops.import_scene.gltf(
                            filepath=output_path,
                            merge_vertices=True
                        )
                    elif self.geshi == '.obj':
                        # 使用新版本OBJ导入器
                        bpy.ops.wm.obj_import(
                            filepath=output_path,
                            forward_axis=get_pre().forward_axis,#'NEGATIVE_Z',#前进轴-z
                            up_axis=get_pre().up_axis,#'Y',#向上y
                            global_scale=scale_factor,
                            use_split_objects=True,
                            use_split_groups=True,
                            collection_separator='/'
                        )
                    # elif self.geshi == '.stl':  # 添加STL支持
                    #     bpy.ops.import_mesh.stl(
                    #         filepath=output_path,
                    #         global_scale=get_pre().global_scale
                    #     )
                except Exception as import_error:
                    self.report({'ERROR'}, f"Import failed.: {str(import_error)}")
                    return {'CANCELLED'}

                # 清理生成文件
                if get_pre().del_gltf:
                    try:
                        os.remove(output_path)
                        # 同时清理关联文件（针对glTF）
                        if self.geshi == '.obj':
                            bin_path = os.path.splitext(output_path)[0] + ".mtl"
                            if os.path.exists(bin_path):
                                os.remove(bin_path)
                    except Exception as e:
                        self.report({'WARNING'}, f"File cleanup failed.: {str(e)}")

                # 正则表达式匹配 . 后面跟着数字的模式
                suffix_pattern = re.compile(r'\.\d+$')

                # 处理新导入的物体
                new_objects = [obj for obj in bpy.context.view_layer.objects if obj not in self.initial_objects]
                try:
                    now = datetime.now()
                    now = int(now.strftime("%Y%m%d%H%M%S"))
                    for obj in new_objects:
                        obj.CADM_obj_Props.from_mayo=True
                        obj.CADM_obj_Props.import_time=now
                        if obj.type == 'MESH':#if hasattr(obj, 'data'):#
                            meshname=obj.data.name
                            match = suffix_pattern.search(obj.data.name)
                            if match:
                                meshname = suffix_pattern.sub('', obj.data.name)
                            obj.CADM_obj_Props.mesh_name=meshname

                            bpy.data.meshes[obj.data.name].CADM_mesh_Props.base_name=meshname
                            bpy.data.meshes[obj.data.name].CADM_mesh_Props.import_time=now
                except:
                    pass
                new_mats = [mat for mat in bpy.data.materials if mat not in self.before_import_mat]
                for mat in new_mats:
                    current_color = mat.diffuse_color
                    mat.diffuse_color = (current_color[0], current_color[1], current_color[2], 1)

                
                empty_object = None
                for obj in new_objects:
                    if obj.type == 'EMPTY':
                        empty_object = obj
                        if get_pre().clean_mat:
                            break
                    if get_pre().clean_mat and obj.type == 'MESH' and obj.data:
                        if obj.material_slots:
                            for solt in obj.material_slots:
                                if solt.material and solt.material in new_mats:
                                    newmat=solt.material
                                    match = suffix_pattern.search(solt.material.name)
                                    if match:
                                        # 删除后缀
                                        base_name = suffix_pattern.sub('', solt.material.name)
                                        oldmat = bpy.data.materials.get(base_name)
                                        if oldmat:
                                            solt.material=oldmat
                                            if newmat.users == 0:
                                                bpy.data.materials.remove(newmat)


                if empty_object and self.geshi == '.gltf':
                    # 设置空物体为活动物体并选中
                    bpy.context.view_layer.objects.active = empty_object
                    empty_object.select_set(True)
                    empty_object.empty_display_size = 1.0
                    # empty_object.empty_display_type = 'CUBE'
                    empty_object.show_name = True
                    empty_object.show_in_front = True

                    # 缩放空物体
                    empty_object.scale = (0.1/scale_factor, 0.1/scale_factor, 0.1/scale_factor)
                # else:
                #     # 取消所有物体的选择
                #     for obj in new_objects:
                #         obj.select_set(False)

                try:
                    if context.space_data.region_3d.view_perspective != 'CAMERA':
                        bpy.ops.view3d.view_selected(use_all_regions=False)
                except:
                    pass
                # elapsed_s = "{:.2f}s".format(time.time() - self.start_time)
                bpy.context.workspace.status_text_set(None)
                # self.report({'INFO'}, f"导入流程完成(Import finished in {elapsed_s})")
                self.report({'INFO'}, _("Import completed in {:.2f}s").format(time.time()-self.start_time))
                return {'FINISHED'}
            # else:

                #     # 检查队列中的输出
                #     try:
                #         while True:
                #             source, line = self.output_queue.get_nowait()
                #             print(f"Waiting Convert 3D file: {line.strip()}")
                #             text=f"Waiting Mayo Convert 3D file: {line.strip()}"
                #             context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context, text,True))
                #             if "100% Imported" in line.strip():
                #                 self.stop_readpro = True
                #                 break
                #     except queue.Empty:
                #         pass

                #     if self.stop_readpro:
                #         context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context,"转换完成，Blender正在导入中..."))
                #     # # self.report({'INFO'}, "stp转换文件中......['ESC'停止导入]")
                #     # # 显示实时进度（示例）
                #     # try:
                #     #     if not self.stop_readpro:
                #     #         # 读取部分输出#self._process.stdout.readline() 是阻塞式的，它会等待一行输出直到有数据可读。如果外部程序在完成时没有正确关闭其标准输出流，这可能会导致 poll() 方法无法及时返回。
                #     #         line = self._process.stdout.readline()
                #     #         if line:
                #     #             if line.strip():
                #     #                 print(f"Waiting Convert 3D file: {line.strip()}")
                #     #             if "100% Imported" in line.strip():#有可能stp文件小捕获不到信息，或是改为出现这些都表示成功了'100%',"100% Imported","100% Exported"
                #     #                 self.stop_readpro=True
                #     #             else:
                #     #                 if line.strip():
                #     #                     text=f"Waiting Mayo Convert 3D file: {line.strip()}"
                #     #                     context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context, text,True))
                #     #                     # bpy.context.workspace.status_text_set(f"['ESC'停止导入] Waiting Mayo {line.strip()}")
                #     #     else:
                #     #         context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context,"转换完成，Blender正在导入中..."))
                #     #         # bpy.context.workspace.status_text_set(f"转换完成，Blender正在导入中...")
                            
                #     # except:
                #     #     pass

        # if event.value == "PRESS" or event.type in {"MOUSEMOVE"}:
        #     return {"RUNNING_MODAL"}

        return {"RUNNING_MODAL"}
        # return {'PASS_THROUGH'}#这个可以让鼠标还能控制

    def execute(self, context):
        # 路径验证增强
        if not os.path.isfile(get_pre().exe_path):
            self.report({'ERROR'}, "mayo-conv.exe path wrong！")
            return {'CANCELLED'}
        if os.path.basename(get_pre().exe_path).lower() != "mayo-conv.exe":
            self.report({'ERROR'}, "The path does not point to mayo-conv.exe!")
            return {'CANCELLED'}
        ini_path = get_ini_directory()
        if not os.path.isfile(ini_path):
            self.report({'ERROR'}, _('No found the mayo-gui.ini file in plugin directory!'))
            return {'CANCELLED'}

        set_inifile_language()

        # 构建输出路径
        input_path = os.path.abspath(self.filepath)
        output_dir = os.path.dirname(input_path)
        output_base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, output_base + self.geshi)

        # 取消所有物体的选择
        for obj in bpy.context.selected_objects:
            obj.select_set(False)

        # 清理旧文件增强
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                self.report({'WARNING'}, f"Can`t delete old mesh model: {str(e)}")

        # 构建正确命令格式
        exe = get_pre().exe_path
        cmd = [
            exe,
            '--use-settings', ini_path,
            input_path,
            '--export', output_path,
            # '--no-progress',#可以返回INFO: "Importing..."但就没有进度了
        ]

        try:
            self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 初始化队列和线程
            self.output_queue = queue.Queue()
            self.output_thread = threading.Thread(target=self.enqueue_output, args=(self._process.stdout, self._process.stderr, self.output_queue))
            self.output_thread.daemon = True
            self.output_thread.start()

        except Exception as proc_error:
            self.report({'ERROR'}, f"Can`t run process: {str(proc_error)}")
            return {'CANCELLED'}

        # 记录初始对象
        self.initial_objects = list(bpy.context.view_layer.objects)
        self.before_import_mat = list(bpy.data.materials)
        # 设置模态计时器

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        # 初始化进度条
        # context.window_manager.progress_begin(0, 100)
        
        return {'RUNNING_MODAL'}

    def enqueue_output(self, out, err, queue):
        for line in iter(out.readline, ''):
            queue.put(('stdout', line))
        out.close()
        
        for line in iter(err.readline, ''):
            queue.put(('stderr', line))
        err.close()

    def cancel(self, context):
        # 清理资源增强
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except:
                pass
            finally:
                self._process = None
        
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

        # 清理生成文件（即使未完成）
        if hasattr(self, 'del_gltf') and get_pre().del_gltf:
            output_path = os.path.join(
                os.path.dirname(self.filepath),
                os.path.splitext(os.path.basename(self.filepath))[0] + self.geshi
            )
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                    # 清理关联文件
                    if self.geshi == '.obj':
                        bin_path = os.path.splitext(output_path)[0] + ".mtl"
                        if os.path.exists(bin_path):
                            os.remove(bin_path)
            except Exception as e:
                self.report({'WARNING'}, f"Can`t delete mesh model: {str(e)}")

        self.report({'INFO'}, "Import has been cancelled.")

def status_bar_draw(self, context,text,importing=False,):
    layout = self.layout
    # if importing:
    layout.label(text="Cancel", icon="EVENT_ESC")
    layout.separator(factor=2.0)
    layout.label(text=f"{text}", icon="TEMP")
    
    

def sna_add_to_topbar_mt_file_import_4A389(self, context):
    self.layout.operator(IMPORT_OT_STEPtoGLTF.bl_idname, text='STEP/IGES (*.step *.stp *.iges *.igs)',emboss=True, depress=False)
        
#TODO:自动更新网格避免重复导入,拖入多个文件,添加导入预设保存;是否可以让mayo直接转换obj和iges两种，然后让用户一次把2种都导入

class IO_FH_Step_Iges(bpy.types.FileHandler):
    bl_idname = "IO_FH_step_iges"
    bl_label = "STEP/IGES"
    bl_import_operator = "import_scene.step_to_gltf"
    bl_file_extensions = ".step;.stp;.iges;.igs"

    @classmethod
    def poll_drop(cls, context):
        return poll_file_object_drop(context)


##为后面自动更新网格准备
class CADM_obj_Props(bpy.types.PropertyGroup):
    from_mayo: BoolProperty(name="From to Mayo",description="",default=False)
    mesh_name: StringProperty(name='mesh name', description='记录网格无后缀的原始名字', default='', subtype='NONE', maxlen=0)
    import_time: FloatProperty(name='import time', description='', default=0.0, subtype='TIME', unit='TIME', step=3, precision=0)

class CADM_mesh_Props(bpy.types.PropertyGroup):
    base_name: bpy.props.StringProperty(name='base name', description='记录网格无后缀的原始名字', default='', subtype='NONE', maxlen=0)
    import_time: bpy.props.FloatProperty(name='import time', description='', default=0.0, subtype='TIME', unit='TIME', step=3, precision=0)

specific_dict = {
    # bl_info 元数据
    ('*', 'This addon lets you import stp/iges files in Blender 4.0+'): '这个插件让你将STEP/IGES文件直接导入Blender 4.0+',
    ('*', 'File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop'): '文件 > 导入 > STEP/IGES (*.step *.stp *.iges *.igs) 或拖放',
    ('*', 'Only Blender 4.0+ versions and Windows are supported'): '仅支持win平台下的 Blender 4.0 及更新版本',

    
    ('*', 'No found the mayo-gui.ini file in plugin directory!'): '！！插件文件夹里没有mayo-gui.ini文件！！',

    # 首选项面板
    ('*', 'Show Options Panel Before Import'): '导入前显示选项面板',
    ('*', 'Display this panel before each import.\nAuto reset on file load/creat new file.\nCan be re-enabled in the plugin settings.'): 
        '始终显示导入选项面板,\n加载/新建文件时自动重置,\n你也可以手动去插件设置里打开面板',
    ('*', 'mayo-conv.exe Path'): 'mayo-conv.exe 路径',
    ('*', '..../mayo-conv.exe (Not mayo.exe)'): '..../mayo-conv.exe 路径(非 mayo.exe)',
    ('*', 'Path to mayo-conv.exe executable'): 'mayo-conv.exe文件路径',
    ('*', 'Convert Target Format'): '转换格式',
    ('*', 'Mayo export format and Blender improt Format'): 'Mayo导出和Blender导入的格式',
    ('*', 'GLTF: Import with empty object hierarchy'): 'GLTF：使用空物体父子层级',
    ('*', 'OBJ: Import with collection hierarchy'): 'OBJ：使用集合层级',
    ('*', 'Mesh Quality'): '网格质量',
    ('*', 'Controls CAD model to mesh conversion precision'): '控制Mayo导入CAD模型后转换到网格的转换精度',
    ('*', 'Very Coarse'): '非常粗糙',
    ('*', 'Fastest conversion with low detail'): '最快转换，细节最少',
    ('*', 'Coarse quality'): '粗糙质量',
    ('*', 'Standard quality'): '标准质量',
    ('*', 'High precision'): '高精度',
    ('*', 'Highest precision'): '最高精度',
    ('*', 'Scale Factor'): '缩放系数',
    ('*', 'Scaling factor for each object in OBJ format,\nScaling factor of the parent empty object in GLTF format'): 
    'OBJ格式导入就是每个物体的缩放系数，\nGLTF格式导入就是父级空物体的缩放系数',
    ('*', 'Del Mesh File After Imported'): '导入后删除网格文件',
    ('*', 'Automatically remove converted files post-import'): '自动删除转换后的中转网格文件',
    ('*', 'Clean Duplicate Materials'): '清理重复材质',
    ('*', 'Remove import-duplicate Materials with .001 suffixes '): '自动移除新导入的材质,判断依据带 .001 后缀',

    # 界面文本
    ('*', 'Settings are temporary - will reset on Blender restart/new file'): '设置为临时生效 - 重启Blender或新建文件后重置',
    ('*', 'Critical Usage Notes:'): '重要提示！',
    ('*', '1. This plugin uses the open-source Mayo to transform CAD models into mesh formats (obj/gltf) for Blender import'): 
        '1. 这个插件通过第三方开源软件Mayo将CAD模型转换为网格文件(obj/gltf),然后导入到Blender',
    ('*', '2. CAD models may contain format-specific parameters from your CAD software. If imported mesh mismatches:'): 
        '2.但你的CAD模型可能从任何你工作的软件里导出的,这些格式有很多不确定的参数,所有如果导入的网格和你的CAD模型不一致：',
    ('*', '   b) Manually import the CAD file in Mayo'): 
        '   b) 在Mayo中手动导入CAD模型',
    ('*', '   a) Start mayo.exe, Adjust parameters under "Tools > Options"'): 
        '   a) 启动mayo.exe软件,在"Tools > Options"中调整导入参数(每次调整后要重新导入模型才有效)',
    ('*', '   c) After optimization, click "Exchange > Save as..." at bottom of Options panel'): 
        '   c) 调整参数到导入的模型网格符合你的要求后，在Options面板底部点击 Exchange->Save as...',
    ('*', '   d) Overwrite the mayo-gui.ini file in plugin directory'): 
        '   d) 覆盖插件目录下的mayo-gui.ini文件',
    ('*', '3. The meshingQuality parameter in the mayo-gui.ini file can be manually set in the import panel.'): 
        '3. mayo-gui.ini文件里的meshingQuality参数可在导入面板里手动设置',
    ('*', '4. Usage: File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop to 3D Viewport'): 
        '4. 使用方法：文件 > 导入 > STEP/IGES 或 直接拖动模型到3D窗口里',

    ('*', 'Sell a plugin ^_~'): '卖个插件 ^_~', 
    ('*', 'A plug-in that can be converted between the collection and the empty object hierarchy!'): 
    '可以在集合与空物体层级之间相互转换的插件',
    ('*', 'Move the empty at the center of the sub-level objects instead of the center of the world coordinates!'): 
    '可以让空物体位于子级物体的中心，而不是世界坐标的中心!',

        # 操作类文本
    ('*', 'Import STEP/IGES'): '导入 STEP/IGES',
    ('*', 'GLTF: Import with empty hierarchy'): 'GLTF：空物体父子层级结构',
    ('*', 'OBJ: Import with collections'): 'OBJ：集合层级结构',
    ('*', 'Lower values = Smaller model'): '数值越小，模型越小',
    ('*', 'Lower values = Larger model'): '数值越小，模型越大',
    ('*', 'Single file import only'): '仅支持单文件导入',
    ('*', 'Mayo Convert CAD model failed: {}'): 'Mayo转换CAD模型失败：{}',
    ('*', 'Please wait,Mayo Converting: {}'): '请稍候，Mayo 转换模型中：{}',
    ('*', 'Converted ,Importing to Blender...'): '模型转换完成,Blender正在导入中...',
    ('*', 'Import completed in {:.2f}s'): '导入完成，耗时 {:.2f} 秒',
    ('*', 'Import has been cancelled.'): '导入操作已中止!',
}
japanese_dict = {
    # bl_info 元数据
    ('*', 'This addon lets you import stp/iges files in Blender 4.0+'): 
        'Blender 4.0+へSTEP/IGESファイルをフォーマット変換でインポート',
    ('*', 'File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop'): 
        'ファイル > インポート > STEP/IGES (*.step *.stp *.iges *.igs) またはドラッグ＆ドロップ',
    ('*', 'Only Blender 4.0+ versions and Windows are supported'): 
        'Windows Blender 4.0以降のバージョンのみ対応',

    ('*', 'No found the mayo-gui.ini file in plugin directory!'): 
        'プラグインディレクトリにmayo-gui.iniファイルが見つかりません！',

    # 首选项面板
    ('*', 'Show Options Panel Before Import'): 
        'インポート前にオプションパネルを表示',
    ('*', 'Display this panel before each import.\nAuto reset on file load/creat new file.\nCan be re-enabled in the plugin settings.'): 
        'インポート前に毎回このパネルを表示します。\nファイルの読み込みや新規作成時に自動的にリセットされます。\nプラグイン設定で再び有効化できます。',
    ('*', 'mayo-conv.exe Path'): 
        'mayo-conv.exeのパス',
    ('*', '..../mayo-conv.exe (Not mayo.exe)'): 
        '..../mayo-conv.exe（mayo.exeではありません）',
    ('*', 'Path to mayo-conv.exe executable'): 
        'mayo-conv.exe実行ファイルのパス',
    ('*', 'Convert Target Format'): 
        'フォーマット変換',
    ('*', 'Mayo export format and Blender improt Format'): 'Mayoでエクスポートし、Blenderでインポートするフォーマット',
    ('*', 'GLTF: Import with empty object hierarchy'): 
        'GLTF：空オブジェクト階層',
    ('*', 'OBJ: Import with collection hierarchy'): 
        'OBJ：コレクション階層',
    ('*', 'Mesh Quality'): 
        'メッシュ品質',
    ('*', 'Controls CAD model to mesh conversion precision'): 
        'CADモデルからメッシュへの変換精度を制御',
    ('*', 'Very Coarse'): 
        '非常に粗い',
    ('*', 'Fastest conversion with low detail'): 
        '最速変換（低詳細）',
    ('*', 'Coarse quality'): 
        '粗い品質',
    ('*', 'Standard quality'): 
        '標準品質',
    ('*', 'High precision'): 
        '高精度',
    ('*', 'Highest precision'): 
        '最高精度',
    ('*', 'Scale Factor'): 
        'スケール係数',
    ('*', 'Scaling factor for each object in OBJ format,\nScaling factor of the parent empty object in GLTF format'): 
        'OBJ形式のインポートは各オブジェクトの拡大縮小係数、\nGLTF形式のインポートは親の空オブジェクトの拡大縮小係数になります',
    ('*', 'Del Mesh File After Imported'): 
        'インポート後メッシュファイルを削除',
    ('*', 'Automatically remove converted files post-import'): 
        '変換済み中間ファイルを自動削除',
    ('*', 'Clean Duplicate Materials'): 
        '重複マテリアルを整理',
    ('*', 'Remove import-duplicate Materials with .001 suffixes '): 
        '.001接尾辞の重複マテリアルを削除',

    # 界面文本
    ('*', 'Settings are temporary - will reset on Blender restart/new file'): 
        '設定は一時的（Blender再起動/新規ファイルでリセット）',
    ('*', 'Critical Usage Notes:'): 
        '重要な使用上の注意：',
    ('*', '1. This plugin uses the open-source Mayo to transform CAD models into mesh formats (obj/gltf) for Blender import'): 
        '1. 本プラグインはMayoを使用してCADモデルをメッシュ形式（obj/gltf）に変換します',
    ('*', '2. CAD models may contain format-specific parameters from your CAD software. If imported mesh mismatches:'): 
        '2. CADモデルに固有のパラメータがある場合、メッシュ不一致が発生する可能性：',
    ('*', '   b) Manually import the CAD file in Mayo'): 
        '   b) MayoでCADファイルを手動インポート',
    ('*', '   a) Adjust parameters under "Tools > Options"'): 
        '   a) "ツール > オプション"でパラメータ調整',
    ('*', '   c) After optimization, click "Exchange > Save as..." at bottom of Options panel'): 
        '   c) 最適化後、"Exchange > Save as..."をクリック',
    ('*', '   d) Overwrite the mayo-gui.ini file in plugin directory'): 
        '   d) プラグインディレクトリのmayo-gui.iniを上書き',
    ('*', '3. The meshingQuality parameter can be auto-configured via import panel settings'): 
        '3. meshingQualityパラメータはインポートパネルで自動設定可能',
    ('*', '4. Usage: File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop to 3D Viewport'): 
        '4. 使用方法：ファイルメニューまたは3Dビューポートへドラッグ＆ドロップ',

    ('*', 'Sell a plugin ^_~'): 
        'プラグイン販売中 ^_~', 
    ('*', 'A plug-in that can be converted between the collection and the empty object hierarchy!'): 
        'コレクションと空オブジェクト階層を相互変換可能なプラグイン',
    ('*', 'Move the empty at the center of the sub-level objects instead of the center of the world coordinates!'): 
        '空オブジェクトを子オブジェクトの中心に配置（ワールド座標中心ではない）',

    # 操作类文本
    ('*', 'Import STEP/IGES'): 
        'STEP/IGESをインポート',
    ('*', 'GLTF: Import with empty hierarchy'): 
        'GLTF：空オブジェクト階層',
    ('*', 'OBJ: Import with collections'): 
        'OBJ：コレクション階層',
    ('*', 'Lower values = Smaller model'): 
        '値が小さいほど縮小',
    ('*', 'Lower values = Larger model'): 
        '値が小さいほど拡大',
    ('*', 'Single file import only'): 
        '単一ファイルのみインポート可能',
    ('*', 'Mayo Convert CAD model failed: {}'): 
        'Mayo CADモデル変換失敗：{}',
    ('*', 'Please wait,Mayo Converting: {}'): 
        '変換中：{}... お待ちください',
    ('*', 'Converted ,Importing to Blender...'): 
        '変換完了、Blenderへインポート中...',
    ('*', 'Import completed in {:.2f}s'): 
        'インポート完了（所要時間：{:.2f}秒）',
    ('*', 'Import has been cancelled.'): 
        'インポートがキャンセルされました',
}

langs = {
    'zh_HANS':specific_dict, 
    'zh_CN':specific_dict,
    'ja_JP': japanese_dict,   
}

classes = (
    MayoConvPreferences,
    IMPORT_OT_STEPtoGLTF,
    IO_FH_Step_Iges,
    CADM_obj_Props,
    CADM_mesh_Props,
)

def register():
    if bpy.app.version < (4, 0, 0):
        print('Only Blender 4.0 and later versions are supported')
        return
    # 检查操作系统
    if sys.platform != 'win32':
        print('This plugin is only supported on Windows')
        return
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Object.CADM_Props = bpy.props.PointerProperty(name='CAD-Model',type=CADM_obj_Props, options={'HIDDEN'})
    bpy.types.Mesh.CADM_Props = bpy.props.PointerProperty(name='CAD-Model',type=CADM_mesh_Props, options={'HIDDEN'})

    bpy.types.TOPBAR_MT_file_import.append(sna_add_to_topbar_mt_file_import_4A389)
    bpy.app.handlers.load_post.append(load_set_show_import_plane_handler)
    bpy.app.translations.register(__package__, langs)
def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)

    del bpy.types.Object.CADM_Props
    del bpy.types.Mesh.CADM_Props
    bpy.types.TOPBAR_MT_file_import.remove(sna_add_to_topbar_mt_file_import_4A389)

    bpy.app.handlers.load_post.remove(load_set_show_import_plane_handler)
    bpy.app.translations.unregister(__package__)
if __name__ == "__main__":
    register()

    bpy.ops.object.empty_image_add(filepath="E:\\My pictur\\original-809518e20eb5c6ea8f5d3405fe30484d.png", align='VIEW', location=(-1.12752, -0.287579, 0.172981), rotation=(1.02655, 1.4934e-07, 0.339823), scale=(1, 1, 1))
