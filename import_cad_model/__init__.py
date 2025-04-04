
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

    if 'meshing' in config and 'meshingQuality' in config['meshing']:

        config['meshing']['meshingQuality'] = self.mesh_quality
    else:

        if 'meshing' not in config:
            config['meshing'] = {}
        config['meshing']['meshingQuality'] = self.mesh_quality
    with open(ini_path, 'w') as configfile:
        config.write(configfile)

def update_chordal_deflection(self, context):
    sna_updated_prop = self.chordal_deflection
    value=(str(round(sna_updated_prop, abs(2))) + 'mm')
    ini_path = get_ini_directory()
    if not os.path.isfile(ini_path):
        print(_('No found the mayo-gui.ini file in plugin directory!'))
        return
    config = configparser.ConfigParser()
    config.read(ini_path)

    if 'meshing' in config and 'meshingchordaldeflection' in config['meshing']:

        config['meshing']['meshingchordaldeflection'] = value
    else:

        if 'meshing' not in config:
            config['meshing'] = {}
        config['meshing']['meshingchordaldeflection'] = value
    with open(ini_path, 'w') as configfile:
        config.write(configfile)

def update_angular_deflection(self, context):
    sna_updated_prop = self.angular_deflection
    value=(str(round(sna_updated_prop, abs(6))) + 'rad')
    ini_path = get_ini_directory()
    if not os.path.isfile(ini_path):
        print(_('No found the mayo-gui.ini file in plugin directory!'))
        return
    config = configparser.ConfigParser()
    config.read(ini_path)

    if 'meshing' in config and 'meshingangulardeflection' in config['meshing']:

        config['meshing']['meshingangulardeflection'] = value
    else:

        if 'meshing' not in config:
            config['meshing'] = {}
        config['meshing']['meshingangulardeflection'] = value
    with open(ini_path, 'w') as configfile:
        config.write(configfile)

def update_relatire(self, context):
    value='ture' if self.relatire else 'false'
    ini_path = get_ini_directory()
    if not os.path.isfile(ini_path):
        print(_('No found the mayo-gui.ini file in plugin directory!'))
        return
    config = configparser.ConfigParser()
    config.read(ini_path)

    if 'meshing' in config and 'meshingrelative' in config['meshing']:

        config['meshing']['meshingrelative'] = value
    else:

        if 'meshing' not in config:
            config['meshing'] = {}
        config['meshing']['meshingrelative'] = value
    with open(ini_path, 'w') as configfile:
        config.write(configfile)

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
        default=True,
        options={'HIDDEN'}
    )
    exe_path: StringProperty(
        name=_("mayo-conv.exe Path"),  
        subtype='FILE_PATH',
        default=_("..../mayo-conv.exe (Not mayo.exe)"),  
        description=_("Path to mayo-conv.exe executable")  
    )
    geshi: bpy.props.EnumProperty(
        name=_('Convert Target Format'),  
        description='Mayo export format and Blender improt Format',
        items=[
            ('.gltf',_(".gltf (by parent Empty object)"), _('GLTF: Import with empty object hierarchy'), 0, 0),  
            ('.obj', _(".obj (by collections)"), _('OBJ: Import with collection hierarchy'), 0, 1)],  
        default='.obj',
    )

    mesh_quality: EnumProperty(
        name=_('Mesh Quality'),  
        description=_('Controls CAD model to mesh conversion precision'),  
        items=[
            ('VeryCoarse', _('Very Coarse'), _('Fastest conversion with low detail'), 0, 0),  
            ('Coarse', _('Coarse Quality'), _('Coarse quality'), 0, 1),  
            ('Normal', _('Normal Quality'), _('Standard quality'), 0, 2),  
            ('Precise', _('Precise Quality'), _('High precision'), 0, 3),  
            ('VeryPrecise', _('Very Precise'), _('Highest precision'), 0, 4),  
            ('UserDefined', _('User Defined'), _('User Defined'), 0, 5)],
        default='Normal',
        update=update_inifile
    )
    chordal_deflection: bpy.props.FloatProperty(name=_('Chordal Deflection(mm)'), 
        description=_('For the tessellation of faces the Chordal Deflection limits the distance between a curve and its tessellation\nThe smaller the value, the more grids.'), 
        default=1.0, subtype='NONE', unit='NONE', min=0.1, step=3, precision=2, update=update_chordal_deflection)
    angular_deflection: bpy.props.FloatProperty(name=_('Angular Deflection'), 
        description=_('For the tessellation of faces the angular deflection limits the angle between subsequent segments in a polyline\nThe smaller the value, the more grids.'), 
        default=0.34906585, subtype='ANGLE', unit='NONE', min=0.01745329, step=3, precision=2, update=update_angular_deflection)
    relatire: bpy.props.BoolProperty(name=_('Relatire'), description=_('Relative computation of edge tolerance.\nIf activated, deflection used for the polygonalisation of each edge will be ChordalDeflection X SizeOfEdge.The deflection used for the faces will be the maximum deflection of their edges.'), 
        default=False, update=update_relatire)

    global_scale:EnumProperty(
        items=[

        ("100", "100.0", "Scale by 100.0"),
        ("10", "10.0", "Scale by 10.0"),
        ("1", "1.0", "Scale by 1.0"),
        ("0.1", "0.1", "Scale by 0.1"),
        ("0.01", "0.01", "Scale by 0.01"),
        ("0.001", "0.001", "Scale by 0.001"),
        ("0.0001", "0.0001", "Scale by 0.0001"),
        ],
        name=_("Scale Factor"),  
        description=_("Scaling factor for each object in OBJ format,\nScaling factor of the parent empty object in GLTF format"),  
        default="1",
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
        default='NEGATIVE_Z',options={'HIDDEN'}
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
        name=_('Del Mesh File After Imported'),  
        description=_('Automatically remove converted files post-import'),  
        default=True,
    )
    clean_mat: BoolProperty(
        name=_('Clean Duplicate Materials'),  
        description=_('Remove import-duplicate Materials with .001 suffixes '),  
        default=True,
    )
    clean_reimport_obj: BoolProperty(
        name=_('Automatically delete duplicate imported objects.'),  
        description=_('Remove duplicate imported objects with .001 suffixes,如果新导入的物体的无后缀网格名已出现当前场景里,并且网格的顶点数一样,则自动删除新导入的'),  
        default=False,
    )
    def draw(self, context):
        layout = self.layout
        row = layout.box().column(align=True)
        row.alert = not os.path.exists(self.exe_path)
        row.scale_x = 1.5
        row.prop(self, "exe_path")

        row = layout.box().column(align=True)
        row.prop(self, "del_gltf")
        row.prop(self, "clean_mat")
        row = layout.box().column(align=True)
        row.label(text=_("Settings are temporary - will reset on Blender restart/new file"), icon="QUESTION")
        row.prop(self, "show_import_plane")

        row = layout.box().column(align=True)

        row.label(text='Critical Usage Notes:', icon="QUESTION")
        row.label(text='1. This plugin uses the open-source Mayo to transform CAD models into mesh formats (obj/gltf) for Blender import')
        row.label(text='2. CAD models may contain format-specific parameters from your CAD software. If imported mesh mismatches:')
        row.label(text='   a) Start mayo.exe, Adjust parameters under "Tools > Options"')
        row.label(text='   b) Manually import the CAD file in Mayo')
        row.label(text='   c) After optimization, click "Exchange > Save as..." at bottom of Options panel')
        row.label(text='   d) Overwrite the mayo-gui.ini file in plugin directory')
        row.label(text='3. The meshing parameter in the mayo-gui.ini file can be manually set in the import panel.')
        row.label(text='4. The exported results of Mayo (GUI app) and mayo-conv may be different, even when using the same settings')
        row.label(text='5. Usage: File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop to 3D Viewport')
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

class IMPORT_OT_STEPtoGLTF(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.step_to_gltf"
    bl_label = "Import STP/IGES(By Mayo)"
    bl_description = "Convert STP/IGES to glTF/obj by Mayo and Import"
    bl_options = {'UNDO'}
    filter_glob: bpy.props.StringProperty(
        default="*.step;*.stp;*.iges;*.igs",
        options={'HIDDEN'},
    )
    directory: bpy.props.StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE', 'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'SKIP_SAVE', 'HIDDEN'})
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_readpro = False
        self._timer = None
        self._process = None
        self.output_queue = None
        self.output_thread = None
    def draw(self, context):
        operator = self
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  
        pre=get_pre()
        layout.label(text='Mayo Export')

        layout.prop(pre, 'geshi')
        layout.prop(pre, 'mesh_quality')
        if pre.mesh_quality=='UserDefined':
            layout.prop(pre, 'chordal_deflection')
            layout.prop(pre, 'angular_deflection')
            layout.prop(pre, 'relatire')
        if bpy.app.version >= (4, 2):
            layout.separator(type="LINE")  
        else:
            layout.label(text='.....................................................')
        layout.label(text='Blender Import')

        layout.prop(pre, 'global_scale')
        if pre.geshi == '.obj':
            layout.prop(pre, 'forward_axis')
            layout.prop(pre, 'up_axis')
        if bpy.app.version >= (4, 2):
            layout.separator(type="LINE")  
        else:
            layout.label(text='.....................................................')
        layout.prop(pre, 'del_gltf')
        layout.prop(pre, 'clean_mat')
        layout.prop(pre, "show_import_plane")
    def invoke(self, context, event):
        self.start_time = time.time()
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

            try:
                while True:
                    source, line = self.output_queue.get_nowait()
                    if "Error" in line.strip():
                        self.report({'ERROR'}, _("Mayo Convert CAD model failed: {},Need to manually try to import the model into Mayo.").format(line.strip()))
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
                context.workspace.status_text_set(lambda self, context: status_bar_draw(self, context,_("Mayo Convert completed, Blender is importing ...")))

            if self._process.poll() is not None:

                print(f"Blender Importing....")

                conttime=time.time()-self.start_time
                startimporttime=time.time()

                context.window_manager.event_timer_remove(self._timer)
                self._timer = None

                output_path = os.path.join(
                    os.path.dirname(self.filepath),
                    os.path.splitext(os.path.basename(self.filepath))[0] + get_pre().geshi
                )

                if not os.path.exists(output_path):
                    self.report({'ERROR'}, f"Mayo Convert CAD model failed,Can`t found exported mesh model: {output_path}")
                    bpy.context.workspace.status_text_set(None)
                    return {'CANCELLED'}

                try:
                    with open(output_path, 'rb') as f_test:
                        pass
                except IOError as e:
                    self.report({'ERROR'}, f"Can`t read exported mesh model: {str(e)}")
                    bpy.context.workspace.status_text_set(None)
                    return {'CANCELLED'}

                scale_factor = float(get_pre().global_scale)
                try:
                    if get_pre().geshi == '.gltf':
                        bpy.ops.import_scene.gltf(
                            filepath=output_path,
                            merge_vertices=True
                        )
                    elif get_pre().geshi == '.obj':

                        bpy.ops.wm.obj_import(
                            filepath=output_path,
                            forward_axis=get_pre().forward_axis,
                            up_axis=get_pre().up_axis,
                            global_scale=scale_factor,
                            use_split_objects=True,
                            use_split_groups=True,
                            collection_separator='/'
                        )

                except Exception as import_error:
                    self.report({'ERROR'}, f"Import failed.: {str(import_error)}")
                    return {'CANCELLED'}

                if get_pre().del_gltf:
                    try:
                        os.remove(output_path)

                        if get_pre().geshi == '.obj':
                            bin_path = os.path.splitext(output_path)[0] + ".mtl"
                            if os.path.exists(bin_path):
                                os.remove(bin_path)
                    except Exception as e:
                        self.report({'WARNING'}, f"File cleanup failed.: {str(e)}")

                suffix_pattern = re.compile(r'\.\d+$')

                new_objects = [obj for obj in bpy.context.view_layer.objects if obj not in self.initial_objects]
                try:
                    now = time.datetime.now()
                    now = int(now.strftime("%Y%m%d%H%M%S"))
                    for obj in new_objects:
                        obj.CADM_obj_Props.from_mayo=True
                        obj.CADM_obj_Props.import_time=now
                        if obj.type == 'MESH':
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

                                        base_name = suffix_pattern.sub('', solt.material.name)
                                        oldmat = bpy.data.materials.get(base_name)
                                        if oldmat:
                                            solt.material=oldmat
                                            if newmat.users == 0:
                                                bpy.data.materials.remove(newmat)
                if empty_object and get_pre().geshi == '.gltf':

                    bpy.context.view_layer.objects.active = empty_object
                    empty_object.select_set(True)
                    empty_object.empty_display_size = 1.0

                    empty_object.show_name = True
                    empty_object.show_in_front = True

                    empty_object.scale = (scale_factor/0.001, scale_factor/0.001, scale_factor/0.001)

                try:
                    if context.space_data.region_3d.view_perspective != 'CAMERA':
                        bpy.ops.view3d.view_selected(use_all_regions=False)
                except:
                    pass

                bpy.context.workspace.status_text_set(None)

                self.report({'INFO'},_("Mayo convert use {:.2f}s,Blender import use {:.2f}s, The entire process took {:.2f}s!").format(conttime,time.time() -  startimporttime,time.time() - self.start_time))
                return {'FINISHED'}

        return {"RUNNING_MODAL"}

    def execute(self, context):

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
        try:
            context.space_data.clip_start=0.001
            context.space_data.clip_end = 100000
        except:
            pass

        input_path = os.path.abspath(self.filepath)
        output_dir = os.path.dirname(input_path)
        output_base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, output_base + get_pre().geshi)

        for obj in bpy.context.selected_objects:
            obj.select_set(False)

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                self.report({'WARNING'}, f"Can`t delete old mesh model: {str(e)}")

        exe = get_pre().exe_path
        cmd = [
            exe,
            '--use-settings', ini_path,
            input_path,
            '--export', output_path,

        ]
        self.start_time = time.time()
        try:
            self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            self.output_queue = queue.Queue()
            self.output_thread = threading.Thread(target=self.enqueue_output, args=(self._process.stdout, self._process.stderr, self.output_queue))
            self.output_thread.daemon = True
            self.output_thread.start()
        except Exception as proc_error:
            self.report({'ERROR'}, f"Can`t run process: {str(proc_error)}")
            return {'CANCELLED'}

        self.initial_objects = list(bpy.context.view_layer.objects)
        self.before_import_mat = list(bpy.data.materials)

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}
    def enqueue_output(self, out, err, queue):
        for line in iter(out.readline, ''):
            queue.put(('stdout', line))
        out.close()
        for line in iter(err.readline, ''):
            queue.put(('stderr', line))
        err.close()
    def cancel(self, context):

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

        if hasattr(self, 'del_gltf') and get_pre().del_gltf:
            output_path = os.path.join(
                os.path.dirname(self.filepath),
                os.path.splitext(os.path.basename(self.filepath))[0] + get_pre().geshi
            )
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)

                    if get_pre().geshi == '.obj':
                        bin_path = os.path.splitext(output_path)[0] + ".mtl"
                        if os.path.exists(bin_path):
                            os.remove(bin_path)
            except Exception as e:
                self.report({'WARNING'}, f"Can`t delete mesh model: {str(e)}")
        self.report({'INFO'}, "Import has been cancelled.")

def status_bar_draw(self, context,text,importing=False,):
    layout = self.layout
    layout.alert = True

    layout.label(text="Cancel", icon="EVENT_ESC")
    layout.separator(factor=2.0)
    layout.label(text=f"{text}", icon="TEMP")

def sna_add_to_topbar_mt_file_import_4A389(self, context):
    self.layout.operator(IMPORT_OT_STEPtoGLTF.bl_idname, text='STEP/IGES (*.step *.stp *.iges *.igs)',emboss=True, depress=False)

class IO_FH_Step_Iges(bpy.types.FileHandler):
    bl_idname = "IO_FH_step_iges"
    bl_label = "STEP/IGES"
    bl_import_operator = "import_scene.step_to_gltf"
    bl_file_extensions = ".step;.stp;.iges;.igs"
    @classmethod
    def poll_drop(cls, context):
        return poll_file_object_drop(context)

class CADM_obj_Props(bpy.types.PropertyGroup):
    from_mayo: BoolProperty(name="From to Mayo",description="",default=False)
    mesh_name: StringProperty(name='mesh name', description='记录网格无后缀的原始名字', default='', subtype='NONE', maxlen=0)
    import_time: FloatProperty(name='import time', description='', default=0.0, subtype='TIME', unit='TIME', step=3, precision=0)

class CADM_mesh_Props(bpy.types.PropertyGroup):
    base_name: bpy.props.StringProperty(name='base name', description='记录网格无后缀的原始名字', default='', subtype='NONE', maxlen=0)
    import_time: bpy.props.FloatProperty(name='import time', description='', default=0.0, subtype='TIME', unit='TIME', step=3, precision=0)

specific_dict = {

    ('*', 'This addon lets you import stp/iges files in Blender 4.0+'): '这个插件让你将STEP/IGES文件直接导入Blender 4.0+',
    ('*', 'File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop'): '文件 > 导入 > STEP/IGES (*.step *.stp *.iges *.igs) 或拖放',
    ('*', 'Only Blender 4.0+ versions and Windows are supported'): '仅支持win平台下的 Blender 4.0 及更新版本',
    ('*', 'No found the mayo-gui.ini file in plugin directory!'): '！！插件文件夹里没有mayo-gui.ini文件！！',

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
    ('*', 'Coarse Quality'): '粗糙质量',
    ('*', 'Coarse quality'): '粗糙质量',
    ('*', 'Normal Quality'): '标准质量',
    ('*', 'Standard quality'): '标准质量',
    ('*', 'Precise Quality'): '高精度',
    ('*', 'High precision'): '高精度',
    ('*', 'Very Precise'): '超高精度',
    ('*', 'Highest precision'): '超高精度',
    ('*', 'User Defined'): '自定义设置',
    ('*', 'Chordal Deflection(mm)'): '弦高公差(mm)',
    ('*', 'For the tessellation of faces the Chordal Deflection limits the distance between a curve and its tessellation\nThe smaller the value, the more grids.'): 
    '弦高公差：限制曲线与网格折线间的最大距离\n数值越小网格越多',
    ('*', 'Angular Deflection'): '角度公差',
    ('*', 'For the tessellation of faces the angular deflection limits the angle between subsequent segments in a polyline\nThe smaller the value, the more grids.'): 
    '角度公差：限制折线相邻线段间的最大角度\n数值越小网格越多',
    ('*', 'Relatire'): '相对公差',
    ('*', 'Relative computation of edge tolerance.\nIf activated, deflection used for the polygonalisation of each edge will be ChordalDeflection X SizeOfEdge.The deflection used for the faces will be the maximum deflection of their edges.'): 
    '边缘公差的相对计算\n如果激活，每个边缘的多边形化使用的偏差将是ChordalDeflection X SizeOfEdge。面使用的偏差将是其边缘的最大偏差。',
    ('*', 'Scale Factor'): '缩放系数',
    ('*', 'Scaling factor for each object in OBJ format,\nScaling factor of the parent empty object in GLTF format'): 
    'OBJ格式导入就是每个物体的缩放系数，\nGLTF格式导入就是父级空物体的缩放系数',
    ('*', 'Del Mesh File After Imported'): '导入后删除网格文件',
    ('*', 'Automatically remove converted files post-import'): '自动删除转换后的中转网格文件',
    ('*', 'Clean Duplicate Materials'): '清理重复材质',
    ('*', 'Remove import-duplicate Materials with .001 suffixes '): '自动移除新导入的材质,判断依据带 .001 后缀',

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
    ('*', '3. The meshing parameter in the mayo-gui.ini file can be manually set in the import panel.'): 
        '3. mayo-gui.ini文件里的meshingQuality参数可在导入面板里手动设置',
    ('*', '4. The exported results of Mayo (GUI app) and mayo-conv may be different, even when using the same settings'): 
        '4.即使在相同的设置下用Mayo.exe直接手动导出的网格和用插件通过指令后台导出的网格效果可能有差异',
    ('*', '5. Usage: File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop to 3D Viewport'): 
        '5. 使用方法：文件 > 导入 > STEP/IGES 或 直接拖动模型到3D窗口里',
    ('*', 'Sell a plugin ^_~'): '卖个插件 ^_~', 
    ('*', 'A plug-in that can be converted between the collection and the empty object hierarchy!'): 
    '可以在集合与空物体层级之间相互转换的插件',
    ('*', 'Move the empty at the center of the sub-level objects instead of the center of the world coordinates!'): 
    '可以让空物体位于子级物体的中心，而不是世界坐标的中心!',

    ('*', 'Import STEP/IGES'): '导入 STEP/IGES',
    ('*', '.gltf (by parent Empty object)'): '.gltf (空物体父子层级结构)',
    ('*', '.obj (by collections)'): '.obj (集合层级结构)',
    ('*', 'Lower values = Smaller model'): '数值越小，模型越小',
    ('*', 'Lower values = Larger model'): '数值越小，模型越大',
    ('*', 'Single file import only'): '仅支持单文件导入',
    ('*', 'Mayo Convert CAD model failed: {},Need to manually try to import the model into Mayo.'): 'Mayo转换CAD模型失败(试试手动去Mayo里导入模型检查下)：{}',
    ('*', 'Please wait,Mayo Converting: {}'): '不要乱点鼠标，请稍候，Mayo 转换模型中：{}',
    ('*', 'Mayo Convert completed, Blender is importing ...'): '模型转换完成,Blender正在导入中...',
    ('*', 'Mayo convert use {:.2f}s,Blender import use {:.2f}s, The entire process took {:.2f}s!'): 
    'Mayo转换模型用时 {:.2f} 秒,Blender 导入用时 {:.2f} 秒, 整个操作耗时 {:.2f} 秒!',
    ('*', 'Import has been cancelled.'): '导入操作已中止!',
}
japanese_dict = {

    ('*', 'This addon lets you import stp/iges files in Blender 4.0+'): 
        'Blender 4.0+へSTEP/IGESファイルをフォーマット変換でインポート',
    ('*', 'File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop'): 
        'ファイル > インポート > STEP/IGES (*.step *.stp *.iges *.igs) またはドラッグ＆ドロップ',
    ('*', 'Only Blender 4.0+ versions and Windows are supported'): 
        'Windows Blender 4.0以降のバージョンのみ対応',
    ('*', 'No found the mayo-gui.ini file in plugin directory!'): 
        'プラグインディレクトリにmayo-gui.iniファイルが見つかりません！',

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
    ('*', '4. The exported results of Mayo (GUI app) and mayo-conv may be different, even when using the same settings'): 
        '4. 同じ設定でMayo.exeを使用して直接手動でエクスポートしたメッシュと、プラグインを使用して指令バックグラウンドでエクスポートしたメッシュの効果は異なる場合があります。',
    ('*', '5. Usage: File > Import > STEP/IGES (*.step *.stp *.iges *.igs) or Drag-and-Drop to 3D Viewport'): 
        '5. 使用方法：ファイルメニューまたは3Dビューポートへドラッグ＆ドロップ',
    ('*', 'Sell a plugin ^_~'): 
        'プラグイン販売中 ^_~', 
    ('*', 'A plug-in that can be converted between the collection and the empty object hierarchy!'): 
        'コレクションと空オブジェクト階層を相互変換可能なプラグイン',
    ('*', 'Move the empty at the center of the sub-level objects instead of the center of the world coordinates!'): 
        '空オブジェクトを子オブジェクトの中心に配置（ワールド座標中心ではない）',

    ('*', 'Import STEP/IGES'): 
        'STEP/IGESをインポート',
    ('*', '.gltf (by parent Empty object)'): 
        'GLTF：空オブジェクト階層',
    ('*', '.obj (by collections)'): 
        'OBJ：コレクション階層',
    ('*', 'Lower values = Smaller model'): 
        '値が小さいほど縮小',
    ('*', 'Lower values = Larger model'): 
        '値が小さいほど拡大',
    ('*', 'Single file import only'): 
        '単一ファイルのみインポート可能',
    ('*', 'Mayo Convert CAD model failed: {},Need to manually try to import the model into Mayo.'): 
        'Mayo CADモデル変換失敗（手動でMayoにモデルをインポートしてみてください）：{}',
    ('*', 'Please wait,Mayo Converting: {}'): 
        '変換中：{}... お待ちください',
    ('*', 'Mayo Convert completed, Blender is importing ...'): 
        '変換完了、Blenderへインポート中...',
    ('*', 'Mayo convert use {:.2f}s,Blender import use {:.2f}s, The entire process took {:.2f}s!'): 
        'Mayo 変換モデルの時間は {:.2f} 秒、Blender のインポート時間は {:.2f} 秒、全体の操作時間は {:.2f} 秒です！',
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
    