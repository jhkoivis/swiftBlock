bl_info = {
    "name": "SwiftBlock",
    "author": "Karl-Johan Nogenmyr, Mikko Folkersma",
    "version": (0, 2),
    "blender": (2, 7, 7),
    "location": "View_3D > Object > SwiftBlock",
    "description": "Writes block geometry as blockMeshDict file",
    "warning": "",
    "wiki_url": "http://openfoamwiki.net/index.php/SwiftBlock",
    "tracker_url": "",
    "category": "OpenFOAM"}

import bpy
import bmesh
import importlib
from . import blockBuilder
importlib.reload(blockBuilder)
from . import blender_utils
importlib.reload(blender_utils)
from . import utils
importlib.reload(utils)


#blocking object name
bpy.types.Object.isblockingObject = bpy.props.BoolProperty(default=False)
bpy.types.Scene.blocking_object = bpy.props.StringProperty(default="")
bpy.types.Object.preview_object = bpy.props.StringProperty(default="")
bpy.types.Object.ispreviewObject = bpy.props.BoolProperty(default=False)


# Initialize all the bmesh layer properties for the blocking object
class InitBlockingObject(bpy.types.Operator):
    bl_idname = "init.blocking"
    bl_label = "Init blocking"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        bpy.ops.object.mode_set(mode='EDIT')
        print("initialize")
        ob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        bm.edges.layers.string.new("type")
        bm.edges.layers.float.new("x1")
        bm.edges.layers.float.new("x2")
        bm.edges.layers.float.new("r1")
        bm.edges.layers.float.new("r2")
        bm.edges.layers.float.new("dx")
        bm.edges.layers.int.new("nodes")
        bm.edges.layers.int.new("groupid")
        bm.edges.layers.string.new("snapId")
        bm.edges.layers.float.new("time")
        bm.faces.layers.int.new("snapId")
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        ob.isblockingObject = True
        context.scene.blocking_object = ob.name
        bpy.ops.set.patchname('INVOKE_DEFAULT')
        return {"FINISHED"}


class ActivateSnap(bpy.types.Operator):
    bl_idname = "activate.snapping"
    bl_label = "Activate snapping object"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        scn = context.scene
        ob = context.active_object
        pob = bpy.data.objects[ob.SnapObject]
        blender_utils.activateObject(pob, False)
        return {'FINISHED'}

class ActivateBlocking(bpy.types.Operator):
    bl_idname = "activate.blocking"
    bl_label = "Activate blocking"
    bl_options = {"UNDO"}

    hide = bpy.props.BoolProperty()

    def invoke(self, context, event):
        scn = context.scene
        ob = bpy.data.objects[scn.blocking_object]
        blender_utils.activateObject(ob, self.hide)
        return {'FINISHED'}

# Get all objects in current context
def getObjects(self, context):
    obs = []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and not ob.isblockingObject and not ob.ispreviewObject:
            obs.append((ob.name, ob.name, ''))
    return obs

# SwiftBlock properties
class BlockProperty(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty()
    block_verts = bpy.props.IntVectorProperty(size = 8)
    enabled = bpy.props.BoolProperty(default=True)
    namedRegion = bpy.props.BoolProperty(default=False)
bpy.utils.register_class(BlockProperty)

# List of block edges (int edgeGroup, int v1, int v2)
class DependentEdgesProperty(bpy.types.PropertyGroup):
    id = bpy.props.IntProperty()
    v1 = bpy.props.IntProperty()
    v2 = bpy.props.IntProperty()
# TODO    snapline = bpy.props.IntProperty()
    # dependent_edge = bpy.props.IntVectorProperty(size = 3)
bpy.utils.register_class(DependentEdgesProperty)

class BlockFacesProperty(bpy.types.PropertyGroup):
    id = bpy.props.IntProperty()
    face_verts = bpy.props.IntVectorProperty(size = 4)
    pos = bpy.props.IntProperty()
    neg = bpy.props.IntProperty()
    enabled = bpy.props.BoolProperty(default=True)
bpy.utils.register_class(BlockFacesProperty)

class EdgeGroupProperty(bpy.types.PropertyGroup):
    group_name = bpy.props.StringProperty()
    group_edges = bpy.props.StringProperty()
bpy.utils.register_class(EdgeGroupProperty)

def initSwiftBlockProperties():
    bpy.types.Object.SnapObject = bpy.props.EnumProperty(name="Object", 
            items=getObjects, description = "The object which has the geometry curves")
    bpy.types.Object.Autosnap = bpy.props.BoolProperty(name="Enable",
            description = "Snap lines automatically from geometry?")
    bpy.types.Object.MappingType = bpy.props.EnumProperty(name="",
            items = (("Geometric1","Geometric1","",1),
                     ("Geometric2","Geometric2","",2),))
    bpy.types.Object.Dx = bpy.props.FloatProperty(name="dx", default=1, update=setCellSize, min=0)
    bpy.types.Object.Nodes = bpy.props.IntProperty(name="Nodes", default=4,  min=2)
    bpy.types.Object.x1 = bpy.props.FloatProperty(name="x1", default=0, description="First cell size", min=0)
    bpy.types.Object.x2 = bpy.props.FloatProperty(name="x2", default=0, description="Last cell size",  min=0)
    bpy.types.Object.r1 = bpy.props.FloatProperty(name="r1", default=1.2, description="First boundary layer geometric ratio", min=1.0)
    bpy.types.Object.r2 = bpy.props.FloatProperty(name="r2", default=1.2, description="Last boundary layer geometric ratio", min=1.0)
    bpy.types.Object.CopyAligned = bpy.props.BoolProperty(name="copyAligned", default=False, description="copy parameters to aligned edges")
    bpy.types.Object.EdgeGroupName = bpy.props.StringProperty(
        name = "Name",default="group name",
        description = "Specify name of edge group")
    bpy.types.Object.bcTypeEnum = bpy.props.EnumProperty(
        items = [('wall', 'wall', 'Defines the patch as wall'),
                 ('patch', 'patch', 'Defines the patch as generic patch'),
                 ('empty', 'empty', 'Defines the patch as empty'),
                 ('symmetryPlane', 'symmetryPlane', 'Defines the patch as symmetryPlane'),
                 ],
        name = "Patch type")
    bpy.types.Object.patchName = bpy.props.StringProperty(
        name = "Patch name",
        description = "Specify name of patch",
        default = "defaultName")

    bpy.types.Object.blocks = \
        bpy.props.CollectionProperty(type=BlockProperty)

    bpy.types.Object.dependent_edges = \
        bpy.props.CollectionProperty(type=DependentEdgesProperty)


    bpy.types.Object.block_faces = \
        bpy.props.CollectionProperty(type=BlockFacesProperty)


    bpy.types.Object.edge_groups = \
        bpy.props.CollectionProperty(type=EdgeGroupProperty)

# Create the swiftBlock panel
class SwiftBlockPanel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "SwiftBlock"
    bl_label = "SwiftBlock"
    # bl_context = "OBJECT"

    def draw(self, context):
        scn = context.scene
        ob = context.active_object
        if not ob:
            return

        box = self.layout.column(align=True)

        if ob.ispreviewObject:
            box = self.layout.box()
            box.operator("activate.blocking", text="Activate blocking").hide = True
        elif scn.blocking_object in bpy.data.objects and ob.name != scn.blocking_object:
            box = self.layout.box()
            box.operator("activate.blocking", text="Activate blocking").hide = False
        elif not ob.isblockingObject:
            box.operator("init.blocking", text="Initialize blocking")

        elif context.active_object and bpy.context.active_object.mode == "EDIT":
            box = self.layout.box()
            box.label("Automatic snapping")
            if ob.Autosnap:
                split = box.split(percentage=0.1)
                col = split.column()
                col.prop(ob, "Autosnap")
                col = split.column()
                col.prop(ob, "SnapObject")
                if ob.SnapObject != "":
                    box.operator("activate.snapping", text="Activate")
            else:
                box.prop(ob, "Autosnap")

            box = self.layout.box()
            box.operator("build.blocking", text="Build Blocking")

            split = box.split()
            split.operator("preview.mesh", text="Preview mesh")
            split = split.split()
            split.operator("write.mesh", text="Write mesh")

            # box.label("Snapping")
            # split = box.split()
            # split.operator("snap.edge", text="Edge to line")
            # split = split.split()
            # split.operator("snap.face", text="Face to surface")

            box = self.layout.box()
            box.label("Line Mapping")
            # box.prop(scn, "MappingType")
            # if scn.MappingType == "Geometric1":
                # box.prop(scn, "Nodes")
            # elif scn.MappingType == "Geometric2":
                # box.prop(scn, "Dx")
            split = box.split()
            col = split.column()
            col.prop(ob, "Nodes")
            col.label("Start")
            col.prop(ob, "x1")
            col.prop(ob, "r1")
            col.operator("set.edge")
            col = split.column()
            col.label('')
            # col.prop(ob, "Dx")
            col.label("End")
            col.prop(ob, "x2")
            col.prop(ob, "r2")
            col.operator("select.aligned")
            split = box.split()
            # split.operator("edge.mapping", text="Set edge")
            # split = split.split()
            box = self.layout.box()
            box.label("Edges")
            box.prop(ob, 'EdgeGroupName')
            box.operator("set.edgegroup")
            for eg in ob.edge_groups:
                split = box.split(percentage=0.5, align=True)
                col = split.column()
                col.operator("get.edgegroup", eg.group_name , emboss=False).egName = eg.group_name
                col = split.column()
                col.operator('del.edgegroup', 'delete').egName = eg.group_name
            box = self.layout.box()
            box.label("Blocks")
            split = box.split(percentage=0.5, align=True)
            col = split.column()
            col.label("Name")
            col = split.column()
            col.label("Id")
            col = split.column()

            for i,bv in enumerate(ob.blocks):
                split = box.split(percentage=0.5, align=True)
                col = split.column()
                c = col.operator("edit.block", ob.blocks[i].name, emboss=False)
                c.blockid = i
                c.name = ob.blocks[i].name

                col = split.column()
                col.label(str(i))
                col = split.column()
                if bv.enabled:
                    c = col.operator('enable.block', 'enabled').blockid = i
                else:
                    c = col.operator('enable.block', 'disabled').blockid = i

            box = self.layout.box()
            box.prop(ob, 'patchName')
            box.prop(ob, 'bcTypeEnum')
            box.operator("set.patchname")
            for m in ob.data.materials:
                try:
                    patchtype = str(' ' + m['patchtype'])
                    split = box.split(percentage=0.2, align=True)
                    col = split.column()
                    col.prop(m, "diffuse_color", text="")
                    col = split.column()
                    col.operator("set.getpatch", text=m.name + patchtype, emboss=False).whichPatch = m.name
                except:
                    pass

class EdgeSelectAligned(bpy.types.Operator):
    bl_idname = "select.aligned"
    bl_label = "Select aligned edges"

    def execute(self, context):
        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        groupl = bm.edges.layers.int.get('groupid')
        for e in bm.edges:
            if e.select:
                groupid = e[groupl]
                for i in bm.edges:
                    if i[groupl] == groupid:
                        i.select = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class EditBlock(bpy.types.Operator):
    bl_idname = "edit.block"
    bl_label = "Edit block"
    bl_options = {'REGISTER', 'UNDO'}


    blockid = bpy.props.IntProperty(name='id')
    # enabled = bpy.props.BoolProperty(name='enabled', default = True)
    namedRegion = bpy.props.BoolProperty(name='Named region', default = False)
    name = bpy.props.StringProperty(name='name')

    def draw(self, context):
        ob = context.active_object
        if not ob.blocks[self.blockid].enabled:
            return
        col = self.layout.column(align = True)
        # col.prop(self, "enabled")
        # split = col.split(percentage=0.1, align=True)
        # col = split.column()
        col.prop(self, "namedRegion")
        if self.namedRegion:
            # col = split.column()
            col.prop(self, "name")

# this could be used to select multiple blocks
    def invoke(self, context, event):
        if event.shift:
            self.shiftDown = True
        else:
            self.shiftDown = False
        self.execute(context)
        return {'FINISHED'}

    def execute(self, context):
        bpy.ops.mesh.select_all(action="DESELECT")
        scn = context.scene
        ob = context.active_object
        ob.blocks[self.blockid].name = self.name
        ob.blocks[self.blockid].namedRegion = self.namedRegion
        ob = context.active_object

        verts = ob.blocks[self.blockid].block_verts

        bm = bmesh.from_edit_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        for v in verts:
            bm.verts[v].select = True
        for f in bm.faces:
            if len(f.verts) == 4 and sum([v.select for v in f.verts]) == 4:
                f.select = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class EnableBlock(bpy.types.Operator):
    bl_idname = "enable.block"
    bl_label = "Enable/disable block"

    blockid = bpy.props.IntProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        block = ob.blocks[self.blockid]
        bm = bmesh.from_edit_mesh(ob.data)
        block_face_verts = [bf.face_verts for bf in ob.block_faces]
        face_verts = []
        for f in bm.faces:
            face_verts.append([v.index for v in f.verts])

        block_faces = utils.getBlockFaces(block.block_verts)
        faces_to_remove = []
        print('Block {} is enabled: {}'.format(self.blockid,block.enabled))
        if block.enabled:
            block.enabled = False
            for f in block_faces:
                fid, tmp = utils.findFace(block_face_verts, f)
                bm.faces.ensure_lookup_table()
                if (ob.block_faces[fid].neg != -1 and ob.block_faces[fid].pos != -1):
                    if ob.block_faces[fid].pos == self.blockid \
                     and ob.blocks[ob.block_faces[fid].neg].enabled:
                        bm.faces.new([bm.verts[v] for v in ob.block_faces[fid].face_verts])
                        ob.block_faces[fid].enabled = True
                    elif ob.blocks[ob.block_faces[fid].pos].enabled:
                        bm.faces.new([bm.verts[v] for v in reversed(ob.block_faces[fid].face_verts)])
                        ob.block_faces[fid].enabled = True
                    else:
                        bmfid = utils.findFace(face_verts,f)[0]
                        faces_to_remove.append(bm.faces[bmfid])
                        ob.block_faces[fid].enabled = False
                else:
                    bmfid = utils.findFace(face_verts,f)[0]
                    faces_to_remove.append(bm.faces[bmfid])
                    ob.block_faces[fid].enabled = False
        else:
            block.enabled = True
            for f in block_faces:
                fid, tmp = utils.findFace(block_face_verts, f)
                bm.faces.ensure_lookup_table()
                if (ob.block_faces[fid].neg != -1 and ob.block_faces[fid].pos != -1):
                    if ob.block_faces[fid].pos == self.blockid \
                     and ob.blocks[ob.block_faces[fid].neg].enabled:
                        bmfid = utils.findFace(face_verts,f)[0]
                        faces_to_remove.append(bm.faces[bmfid])
                        ob.block_faces[fid].enabled = False
                    elif ob.block_faces[fid].neg == self.blockid \
                     and ob.blocks[ob.block_faces[fid].pos].enabled:
                        bmfid = utils.findFace(face_verts,f)[0]
                        faces_to_remove.append(bm.faces[bmfid])
                        ob.block_faces[fid].enabled = False
                    else:
                        if ob.block_faces[fid].neg != -1:
                            bm.faces.new([bm.verts[v] for v in ob.block_faces[fid].face_verts])
                            ob.block_faces[fid].enabled = True
                        else:
                            bm.faces.new([bm.verts[v] for v in reversed(ob.block_faces[fid].face_verts)])
                            ob.block_faces[fid].enabled = True
                else:
                    if ob.block_faces[fid].neg != -1:
                        bm.faces.new([bm.verts[v] for v in ob.block_faces[fid].face_verts])
                        ob.block_faces[fid].enabled = True
                    else:
                        bm.faces.new([bm.verts[v] for v in reversed(ob.block_faces[fid].face_verts)])
                        ob.block_faces[fid].enabled = True

        for f in faces_to_remove:
            bm.faces.remove(f)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class DelEdgeGroup(bpy.types.Operator):
    bl_idname = "del.edgegroup"
    bl_label = "Get edge group"

    egName = bpy.props.StringProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        for i,eg in enumerate(ob.edge_groups):
            if eg.group_name == self.egName:
                ob.edge_groups.remove(i)
                return {'FINISHED'}
        return {'CANCEL'}

class GetEdgeGroup(bpy.types.Operator):
    bl_idname = "get.edgegroup"
    bl_label = "Get edge group"

    egName = bpy.props.StringProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.mesh.select_all(action="DESELECT")

        bm = bmesh.from_edit_mesh(ob.data)
        for eg in ob.edge_groups:
            if eg.group_name == self.egName:
                edges = list(map(int,eg.group_edges.split(',')))
                for e in edges:
                    bm.edges[e].select = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class SetEdgeGroup(bpy.types.Operator):
    '''Set the given name to the selected edges'''
    bl_idname = "set.edgegroup"
    bl_label = "Set edge group"

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        edges = []
        for e in ob.data.edges:
            if e.select:
                edges.append(e.index)
        edgesstr = ','.join(map(str,edges))
        for e in ob.edge_groups:
            if e.group_name == ob.EdgeGroupName:
                e.group_edges = edgesstr
                return {'FINISHED'}
        eg = ob.edge_groups.add()
        eg.group_name = ob.EdgeGroupName
        eg.group_edges = edgesstr
        return {'FINISHED'}

def patchColor(patch_no):
    color = [(0.25,0.25,0.25), (1.0,0.,0.), (0.0,1.,0.),(0.0,0.,1.),(0.707,0.707,0),(0,0.707,0.707),(0.707,0,0.707)]
    return color[patch_no % len(color)]

class OBJECT_OT_SetPatchName(bpy.types.Operator):
    '''Set the given name to the selected faces'''
    bl_idname = "set.patchname"
    bl_label = "Set name"

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        NoSelected = 0
        for f in ob.data.polygons:
            if f.select:
                NoSelected += 1
        if NoSelected:
            namestr = ob.patchName
            namestr = namestr.strip()
            namestr = namestr.replace(' ', '_')
            try:
                mat = bpy.data.materials[namestr]
                patchindex = list(ob.data.materials).index(mat)
                ob.active_material_index = patchindex
            except: # add a new patchname (as a blender material, as such face props are conserved during mesh mods)
                mat = bpy.data.materials.new(namestr)
                mat.diffuse_color = patchColor(len(ob.data.materials))
                bpy.ops.object.material_slot_add()
                ob.material_slots[-1].material = mat
            mat['patchtype'] = ob.bcTypeEnum
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.material_slot_assign()
        else:
            self.report({'INFO'}, "No faces selected!")
            return{'CANCELLED'}
        return {'FINISHED'}

class OBJECT_OT_GetPatch(bpy.types.Operator):
    '''Click to select faces belonging to this patch'''
    bl_idname = "set.getpatch"
    bl_label = "Get patch"

    whichPatch = bpy.props.StringProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,False,True)")
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        mat = bpy.data.materials[self.whichPatch]
        patchindex = list(ob.data.materials).index(mat)
        ob.active_material_index = patchindex
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.material_slot_select()
        ob.bcTypeEnum = mat['patchtype']
        ob.patchName = self.whichPatch
        return {'FINISHED'}


# Change the layer properties of currently selected edges
class SetEdge(bpy.types.Operator):
    bl_idname = "set.edge"
    bl_label = "Set edge"
    bl_options = {"UNDO"}

    def execute(self, context):
        ob = context.active_object
        scn = context.scene
        if not ob.blocks:
            bpy.ops.build.blocking('INVOKE_DEFAULT')

        bm = bmesh.from_edit_mesh(ob.data)
        typel = bm.edges.layers.string.get('type')
        x1l = bm.edges.layers.float.get('x1')
        x2l = bm.edges.layers.float.get('x2')
        r1l = bm.edges.layers.float.get('r1')
        r2l = bm.edges.layers.float.get('r2')
        nodesl = bm.edges.layers.int.get('nodes')

        for e in bm.edges:
            if e.select:
                # if ob.CopyAligned:
                    # groupid = e[groupl]
                    # for i in bm.edges:
                        # if i[groupl] == groupid:
                            # i.select = True
                e[typel] = str.encode(ob.MappingType)
                e[nodesl] = ob.Nodes
                e[x1l] = ob.x1
                e[x2l] = ob.x2
                e[r1l] = ob.r1
                e[r2l] = ob.r2
        return {'FINISHED'}

def setCellSize(self, context):
    ob = context.active_object
    scn = context.scene

    bm = bmesh.from_edit_mesh(ob.data)
    typel = bm.edges.layers.string.get('type')
    x1l = bm.edges.layers.float.get('x1')
    x2l = bm.edges.layers.float.get('x2')
    r1l = bm.edges.layers.float.get('r1')
    r2l = bm.edges.layers.float.get('r2')
    nodesl = bm.edges.layers.int.get('nodes')

    for e in bm.edges:
        if e.select:
            e[typel] = str.encode(ob.MappingType)
            L = (e.verts[0].co-e.verts[1].co).length
            N=utils.getNodes(ob.x1,ob.x2,ob.r1,ob.r2,L,ob.Dx)
            e[nodesl] = N
            e[x1l] = ob.x1
            e[x2l] = ob.x2
            e[r1l] = ob.r1
            e[r2l] = ob.r2

# Explicitly define which line to snap for a edge
# Not fully functional
class SnapToEdge(bpy.types.Operator):
    bl_idname = "snap.edge"
    bl_label = "Snap edge to line"
    bl_options = {"UNDO"}

    def modal(self, context, event):
        # assign to vertex group
        if event.type in {'RET', 'RIGHTMOUSE'}:
            edges_selected = False
            for e in self.gob.data.edges:
                if e.select:
                    edges_selected = True
                    break
            if edges_selected:
                bpy.ops.object.vertex_group_add()
                bpy.ops.object.vertex_group_assign()
                vgname = self.gob.vertex_groups.active.name
                # Convert to 64 bit because otherwise "TypeError: expected an int, not a int"
                # vgid = uuid.uuid1().int >> 64 
            else:
                vgname = ""
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.scene.objects.active = self.bob
            bpy.ops.object.mode_set(mode='EDIT')

            bm = bmesh.from_edit_mesh(self.bob.data)
            snapl = bm.edges.layers.string.get('snapId')

            for e in bm.edges:
                if e.select:
                    e[snapl] = vgname.encode()
                    edges_selected = True
            return {"FINISHED"}

        elif event.type in {'ESC'}:
            # self.bob.hide = False
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.scene.objects.active = self.bob
            bpy.ops.object.mode_set(mode='EDIT')
            return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        # self.bob = bpy.data.objects[context.scene.BlockingObject]
        self.bob = context.active_object
        self.gob = bpy.data.objects[context.scene.SnapObject]
        # self.bob.hide = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.objects.active = self.gob
        bpy.ops.object.mode_set(mode='EDIT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

# Explicitly define which surface to snap for a face
# Not implemented
class SnapToSurface(bpy.types.Operator):
    bl_idname = "snap.face"
    bl_label = "Snap face to surface"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        return {"FINISHED"}

# Automatically find blocking for the object and preview it.
class BuildBlocking(bpy.types.Operator):
    bl_idname = "build.blocking"
    bl_label = "Build blocks"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        # get verts and edges
        ob = context.active_object
        mesh = ob.data
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        verts = []
        edges = []
        # edgeDict turha taalla?
        edgeDict = dict()
        for v in mesh.vertices:
            verts.append(v.co)
        for e in mesh.edges:
            edges.append([e.vertices[0],e.vertices[1]])
            edgeDict[(e.vertices[0],e.vertices[1])] = e.index
        disabled = []
        # for b in ob.blocks:
            # if not b.enabled:
                # disabled.extend(b.block_verts)
        # find blocking
        log, block_verts, dependent_edges, face_info, all_edges, faces_as_list_of_nodes = blockBuilder.blockFinder(edges,verts,disabled = disabled)

        ob.blocks.clear()
        for i,bv in enumerate(block_verts):
            b = ob.blocks.add()
            b.name = 'block_{}'.format(i)
            b.block_verts = bv

        # bm = bmesh.new()
        bm = bmesh.from_edit_mesh(ob.data)
        # bm.from_mesh(ob.data)
        groupl = bm.edges.layers.int.get('groupid')

        ob.dependent_edges.clear()
        for i, g in enumerate(dependent_edges):
            for e in g:
                bm.edges.ensure_lookup_table()
                de = ob.dependent_edges.add()
                # de.dependent_edge = (i, e[0], e[1])
                de.id = i
                de.v1 = e[0]
                de.v2 = e[1]
                if (e[0],e[1]) in edgeDict:
                    be = bm.edges[edgeDict[(e[0],e[1])]]
                else:
                    be = bm.edges[edgeDict[(e[1],e[0])]]
                be[groupl] = i
        faces = []
        for f in bm.faces:
            faces.append([v.index for v in f.verts])

        decrease = 0
        block_ids = []
        for key in face_info.keys():
            block_ids.extend(face_info[key]['pos'])
            block_ids.extend(face_info[key]['neg'])
        if max(block_ids) > len(ob.blocks)-1:
            decrease = 1
        ob.block_faces.clear()
        for fid, fn in enumerate(faces_as_list_of_nodes):
            f = ob.block_faces.add()
            f.id = utils.findFace(faces,fn)[0]
            f.enabled = True
            f.face_verts = fn
            if face_info[fid]['pos']:
                f.pos = face_info[fid]['pos'][0] - decrease
            else:
                f.pos = -1
            if face_info[fid]['neg']:
                f.neg = face_info[fid]['neg'][0] - decrease
            else:
                f.neg = -1

        bpy.ops.object.mode_set(mode='OBJECT')

        edgeDirections = utils.getEdgeDirections(block_verts, dependent_edges)

        ob = bpy.context.active_object
        me = ob.data
        edgelist = dict()
        for e in me.edges:
            edgelist[(e.vertices[0],e.vertices[1])] = e.index
        for ed in edgeDirections:
            # consistentEdgeDirs(ed)
            for e in ed:
                if (e[0],e[1]) not in edgelist:
                    ei = me.edges[edgelist[(e[1],e[0])]]
                    (e0, e1) = ei.vertices
                    ei.vertices = (e1, e0)
        bpy.ops.object.mode_set(mode='EDIT')

        repair_faces(face_info, faces_as_list_of_nodes)
        self.report({'INFO'}, "Number of blocks: {}".format(len(block_verts)))
		# blender_utils.draw_edge_direction()
        return {"FINISHED"}


# Build the mesh from already existing blocking
def writeMesh(ob, filename = ''):
    verts = list(blender_utils.vertices_from_mesh(ob))
    edges = list(blender_utils.edges_from_mesh(ob))

    bpy.ops.object.mode_set(mode='OBJECT')

    ob.select = False
    if ob.Autosnap:
        polyLines, polyLinesPoints, lengths = getPolyLines(verts,edges,ob)
    else:
        polyLines = []
        lengths = [[]]

    verts = []
    matrix = ob.matrix_world.copy()
    for v in ob.data.vertices:
        verts.append(matrix*v.co)

    if not ob.blocks:
        bpy.ops.build.blocking('INVOKE_DEFAULT')
    blocks = []
    block_names = []
    for b in ob.blocks:
        if b.enabled:
            blocks.append(list(b.block_verts))
            if b.namedRegion:
                block_names.append(b.name)
            else:
                block_names.append('')

    edgeInfo = collectEdges(ob,lengths)
    detemp = []
    ngroups = 0
    for de in ob.dependent_edges:
        detemp.append((de.id,de.v1,de.v2))
        ngroups = max(ngroups,int(de.id))

    dependent_edges = [[] for i in range(ngroups+1)]
    for e in detemp:
        dependent_edges[e[0]].append([e[1],e[2]])

    block_faces = []
    for f in ob.block_faces:
        if f.enabled:
            block_faces.append(list(f.face_verts))

    patchnames = list()
    patchtypes = list()
    patchverts = list()
    patches = list()
    bpy.ops.object.mode_set(mode='EDIT')
    for mid, m in enumerate(ob.data.materials):
        bpy.ops.mesh.select_all(action='DESELECT')
        ob.active_material_index = mid
        bpy.ops.object.material_slot_select()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        faces = ob.data.polygons
        for f in faces:
            if f.select and f.material_index == mid:
                if m.name in patchnames:
                    ind = patchnames.index(m.name)
                    patchverts[ind].append(list(f.vertices))
                else:
                    patchnames.append(m.name)
                    patchtypes.append(m['patchtype'])
                    patchverts.append([list(f.vertices)])

    for ind,pt in enumerate(patchtypes):
        patches.append([pt])
        patches[ind].append(patchnames[ind])
        patches[ind].append(patchverts[ind])
### This is everything that is related to blockMesh so a new multiblock mesher could be introduced easily just by creating new preview file ###
    from . import preview
    importlib.reload(preview)
    if filename:
        mesh = preview.PreviewMesh(filename)
    else:
        mesh = preview.PreviewMesh()
    cells = mesh.writeBlockMeshDict(verts, 1, patches, polyLines, edgeInfo, block_names, blocks, dependent_edges, block_faces)
###############################################################
    return mesh, cells

class WriteMesh(bpy.types.Operator):
    bl_idname = "write.mesh"
    bl_label = "Write Mesh"

    filepath = bpy.props.StringProperty(
            name="File Path",
            description="Filepath used for exporting the file",
            maxlen=1024,
            subtype='FILE_PATH',
            default='/opt',
            )
    check_existing = bpy.props.BoolProperty(
            name="Check Existing",
            description="Check and warn on overwriting existing files",
            default=True,
            options={'HIDDEN'},
            )


    def invoke(self, context, event):
        bpy.context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        ob = context.active_object
        mesh, cells = writeMesh(ob, self.filepath)
        self.report({'INFO'}, "Cells in mesh: " + str(cells))
        return {"FINISHED"}

class PreviewMesh(bpy.types.Operator):
    bl_idname = "preview.mesh"
    bl_label = "Preview mesh"
    bl_options = {"UNDO"}

    filename = bpy.props.StringProperty(default='')

    def invoke(self, context, event):
        ob = context.active_object
        mesh, cells = writeMesh(ob)
        points, faces = mesh.runMesh()
        blender_utils.previewMesh(ob, points, faces)
        self.report({'INFO'}, "Cells in mesh: " + str(cells))
        return {"FINISHED"}


# Kalle's implementation
def repair_faces(face_info, faces_as_list_of_nodes):
    ob = bpy.context.active_object
    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,False,True)")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for f in ob.data.polygons:
        fid, tmp = utils.findFace(faces_as_list_of_nodes, f.vertices)
        if fid >= 0: # face was found in list
            if (len(face_info[fid]['neg']) + len(face_info[fid]['pos'])) > 1: #this is an internal face
                f.select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='ONLY_FACE')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    presentFaces = []

    for f in ob.data.polygons:
        presentFaces.append(list(f.vertices))

    for faceid, f in enumerate(faces_as_list_of_nodes):
        if (len(face_info[faceid]['neg']) + len(face_info[faceid]['pos'])) == 1: #this is a boundary face
            fid, tmp = utils.findFace(presentFaces, f)
            if fid < 0: # this boundary face does not exist as a blender polygon. lets create one!
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode='OBJECT')
                for v in f:
                    ob.data.vertices[v].select = True
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.edge_face_add()
                bpy.ops.mesh.tris_convert_to_quads(uvs=False, vcols=False, sharp=False, materials=False)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')


def get_snap_vertices(bob):
    gob = bpy.data.objects[bpy.context.scene.SnapObject]
    # vg = gob.vertex_groups.get(str(snapId))

    group_lookup = {g.index: g.name for g in gob.vertex_groups}
    verts = {name: [] for name in group_lookup.values()}
    for v in gob.data.vertices:
        for g in v.groups:
            verts[group_lookup[g.group]].append(v.index)

    for key, value in verts.items() :
        bm = bmesh.new()
        bm.from_mesh(gob.data)
        bm.select_mode = {"VERT","EDGE"}
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        edges = []
        averts = []
        bm.verts.ensure_lookup_table()
        for v in value:
            bm.verts[v].select = True
        bm.select_flush(True)
        bm.select_flush_mode()
        for e in bm.edges:
            if e.select:
                edges.append((e.verts[0].index,e.verts[1].index))
        if edges:
            vertids = utils.sortEdges(edges)
        verts[key] = [gob.data.vertices[vid].co for vid in vertids]
    return verts

def collectEdges(bob, lengths):
    bob.select = True
    bpy.context.scene.objects.active = bob
    bpy.ops.object.mode_set(mode='EDIT')
    # snap_vertices = get_snap_vertices(bob)
    bm = bmesh.from_edit_mesh(bob.data)
    layers = bm.edges.layers
    snapIdl = layers.string.get('snapId')
    block_edges = dict()
    def getDefault(e, var, prop):
        if type(prop) is float:
            val = e[layers.float.get(var)]
        elif type(prop) is int:
            val = e[layers.int.get(var)]
        if val == 0:
            val = prop
        return val

    for e in bm.edges:
        be = dict()
        ev = list([e.verts[0].index,e.verts[1].index])
        if ev in lengths[0]:
            ind = lengths[0].index(ev)
            L = lengths[1][ind]
        else:
            L = (e.verts[0].co-e.verts[1].co).length
        be["type"] = e[layers.string.get("type")].decode()
        be["x1"] = getDefault(e, "x1", bob.x1)
        be["x2"] = getDefault(e, "x2", bob.x2)
        be["r1"] = getDefault(e, "r1", bob.r1)
        be["r2"] = getDefault(e, "r2", bob.r2)
        be["N"] = getDefault(e, "nodes", bob.Nodes)
        be["L"] = L
        be = utils.edgeMapping(be)
        block_edges[(e.verts[0].index,e.verts[1].index)] = be
        be = dict(be)
        be["x1"],be["x2"] = be["x2"],be["x1"]
        be["r1"],be["r2"] = be["r2"],be["r1"]
        be = utils.edgeMapping(be)

        block_edges[(e.verts[1].index,e.verts[0].index)] = be

        # if e[snapIdl]:
            # verts = snap_vertices[e[snapIdl].decode()]
            # if (verts[0]-e.verts[0].co).length < (verts[0] - e.verts[1].co).length:
                # be["verts"] = verts
            # else:
                # verts = list(reversed(verts))
                # be["verts"] = verts
        # else:
            # be["verts"] = (e.verts[0].co,e.verts[1].co)
    return block_edges

# Kalle's implementation
def getPolyLines(verts, edges, bob):
    scn = bpy.context.scene
    polyLinesPoints = []
    polyLines = ''
    polyLinesLengths = [[], []]
    tol = 1e-6

    def isPointOnEdge(point, A, B):
        eps = (((A - B).magnitude - (point-B).magnitude) - (A-point).magnitude)
        return True if (abs(eps) < tol) else False

    # nosnap= [False for i in range(len(edges))]
    # for eid, e in enumerate(obj.data.edges):
        # nosnap[eid] = e.use_edge_sharp

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    geoobj = bpy.data.objects[bob.SnapObject]
    geo_verts = list(blender_utils.vertices_from_mesh(geoobj))
    geo_edges = list(blender_utils.edges_from_mesh(geoobj))
    geoobj.select = False # avoid deletion

# First go through all vertices in the block structure and find vertices snapped to edges
# When found, add a vertex at that location to the polyLine object by splitting the edge
# Create a new Blender object containing the newly inserted verts. Then use Blender's
# shortest path algo to find polyLines.

    for vid, v in enumerate(verts):
        found = False
        for gvid, gv in enumerate(geo_verts):
            mag = (v-gv).magnitude
            if mag < tol:
                found = True
                break   # We have found a vertex co-located, continue with next block vertex
        if not found:
            for geid, ge in enumerate(geo_edges):
                if (isPointOnEdge(v, geo_verts[ge[0]], geo_verts[ge[1]])):
                    geo_verts.append(v)
                    geo_edges.append([geo_edges[geid][1],len(geo_verts)-1]) # Putting the vert on the edge, by splitting it in two.
                    geo_edges[geid][1] = len(geo_verts)-1
                    break # No more iteration, go to next block vertex

    mesh_data = bpy.data.meshes.new("deleteme")
    mesh_data.from_pydata(geo_verts, geo_edges, [])
    mesh_data.update()
    geoobj = bpy.data.objects.new('deleteme', mesh_data)
    bpy.context.scene.objects.link(geoobj)
    geo_verts = list(blender_utils.vertices_from_mesh(geoobj))
    geo_edges = list(blender_utils.edges_from_mesh(geoobj))
    bpy.context.scene.objects.active=geoobj

# Now start the search over again on the new object with more verts
    snapped_verts = {}
    for vid, v in enumerate(verts):
        for gvid, gv in enumerate(geo_verts):
            mag = (v-gv).magnitude
            if mag < tol:
                snapped_verts[vid] = gvid
                break   # We have found a vertex co-located, continue with next block vertex

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    for edid, ed in enumerate(edges):
        if ed[0] in snapped_verts and ed[1] in snapped_verts:# and not nosnap[edid]:
            geoobj.hide = False
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            geoobj.data.vertices[snapped_verts[ed[0]]].select = True
            geoobj.data.vertices[snapped_verts[ed[1]]].select = True
            bpy.ops.object.mode_set(mode='EDIT')
            try:
                bpy.ops.mesh.select_vertex_path(type='EDGE_LENGTH')
            except:
                bpy.ops.mesh.shortest_path_select()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.duplicate()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set(mode='OBJECT')
            polyLineobj = bpy.data.objects['deleteme.001']
            if len(polyLineobj.data.vertices) > 2:
                polyLineverts = list(blender_utils.vertices_from_mesh(polyLineobj))
                polyLineedges = list(blender_utils.edges_from_mesh(polyLineobj))
                for vid, v in enumerate(polyLineverts):
                    mag = (v-verts[ed[0]]).magnitude
                    if mag < tol:
                        startVertex = vid
                        break
                polyLineStr, vectors, length = sortedVertices(polyLineverts,polyLineedges,startVertex)
                polyLinesPoints.append([ed[0],ed[1],vectors])
                polyLinesLengths[0].append([min(ed[0],ed[1]), max(ed[0],ed[1])]) # write out sorted
                polyLinesLengths[1].append(length)
                polyLine = 'polyLine {} {} ('.format(*ed)
                polyLine += polyLineStr
                polyLine += ')\n'
                polyLines += polyLine

            geoobj.select = False
            polyLineobj.select = True
            bpy.ops.object.delete()
    geoobj.select = True
    bpy.ops.object.delete()
    return polyLines, polyLinesPoints, polyLinesLengths

def sortedVertices(verts,edges,startVert):
    sorted = []
    vectors = []
    sorted.append(startVert)
    vert = startVert
    length = len(edges)+1
    for i in range(len(verts)):
        for eid, e in enumerate(edges):
            if vert in e:
                if e[0] == vert:
                    sorted.append(e[1])
                else:
                    sorted.append(e[0])
                edges.pop(eid)
                vert = sorted[-1]
                break

    polyLine = ''
    length = 0.
    for vid, v in enumerate(sorted):
        polyLine += '({} {} {})'.format(*verts[v])
        vectors.append(verts[v])
        if vid>=1:
            length += (vectors[vid] - vectors[vid-1]).magnitude
    return polyLine, vectors, length

initSwiftBlockProperties()
def register():
    bpy.utils.register_module(__name__)
def unregister():
    bpy.utils.unregister_module(__name__)
if __name__ == "__main__":
        register()
