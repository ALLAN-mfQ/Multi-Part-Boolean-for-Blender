bl_info = {
    "name": "Multi-Part Boolean", 
    "author": "ALLAN-mfQ",
    "version": (1, 0, 0), 
    "blender": (4, 3, 0),
    "location": "3D View > Sidebar > Multi-Part Boolean",
    "description": "Automatically splits both base and cutter objects by their disconnected mesh parts, applies boolean operations to all combinations, and joins the results. Results are stored in a new collection each time.", # Descriptionも英語に
    "category": "Object",
}

import bpy
import bmesh
import time
import json
from bpy.types import Scene, Operator, Panel, PropertyGroup
from bpy.props import EnumProperty, StringProperty, PointerProperty
from bpy.app.translations import pgettext # 翻訳用関数

# --- 翻訳辞書 ---
translations_dict = {
    "ja_JP": {
        ("*", "Multi-Part Boolean"): "マルチパート・ブーリアン",
        ("*", "1. Object Selection and Settings:"): "1. オブジェクト選択と設定:",
        ("*", "Operation"): "演算",
        ("*", "Difference"): "差分",
        ("*", "Cuts the cutter from the base"): "ベースからカッターを削る",
        ("*", "Intersect"): "交差",
        ("*", "Keeps the common part of the base and cutter"): "ベースとカッターの共通部分を保持",
        ("*", "2. Execute Process:"): "2. 処理実行:",
        ("*", "Execute Batch Boolean Process"): "ブーリアン処理を一括実行",
        ("*", "Batch Boolean Process"): "一括ブーリアン処理",
        ("*", "Select at least two objects: a base (active) and a cutter."): "ベース（アクティブ）とカッターを少なくとも2つ選択してください。",
        ("*", "Active object (base) is missing."): "アクティブオブジェクト（ベース）がありません。",
        ("*", "No valid mesh cutter selected."): "有効なメッシュカッターが選択されていません。",
        ("*", "Base and cutter must both be mesh objects."): "ベースとカッターは両方ともメッシュオブジェクトである必要があります。",
        ("*", "Batch boolean process started."): "一括ブーリアン処理を開始しました。",
        ("*", "Created new result collection: '{coll_name}'"): "新しい結果コレクション '{coll_name}' を作成しました。",
        ("*", "Error during part-wise boolean addition."): "パーツ毎のブーリアン追加処理でエラーが発生しました。",
        ("*", "Could not retrieve list of objects with boolean modifiers: {error}"): "ブーリアンモディファイアが追加されたオブジェクトのリストを取得できませんでした: {error}",
        ("*", "No objects with boolean modifiers found (list is empty)."): "ブーリアンモディファイアが追加されたオブジェクトが見つかりません (リストが空)。",
        ("*", "Error during modifier application and join process."): "モディファイア適用と結合処理でエラーが発生しました。",
        ("*", "Batch boolean process completed. Result: '{result_name}' in collection '{coll_name}'"): "一括ブーリアン処理が完了しました。結果はコレクション '{coll_name}' の '{result_name}' です。",
        ("*", "Batch boolean process completed. Result: Unknown in collection '{coll_name}'"): "一括ブーリアン処理が完了しました。結果はコレクション '{coll_name}' の 不明 です。",
        ("*", "Add Boolean Modifiers per Part (Internal)"): "パーツ毎にブーリアン追加 (内部処理)",
        ("*", "Apply Modifiers and Join (Internal)"): "モディファイア適用と結合 (内部処理)",
        ("*", "Internal Error: Could not find object or collection - {error}"): "内部エラー: オブジェクトまたはコレクションが見つかりません - {error}",
        ("*", "No valid base parts were created."): "有効なベースパーツが作成されませんでした。",
        ("*", "No valid cutter parts were created."): "有効なカッターパーツが作成されませんでした。",
        ("*", "Internal Error: Failed to load properties - {error}"): "内部エラー: プロパティの読み込みに失敗 - {error}",
        ("*", "Internal Error: No target objects for apply."): "(内部)適用対象オブジェクトがありません",
        ("*", "Internal Error: No valid active object for join."): "(内部)結合対象の有効なアクティブオブジェクトがありません",
        ("*", "Internal Error: Join failed (None)."): "(内部)Join失敗(None)",
        ("*", "Internal Error: Join error: {error}"): "(内部)Joinエラー: {error}",
        ("*", "Creates a new collection and generates the result."): "新規コレクションを作成し結果を生成します",
    }
}

# --- プロパティの定義 ---
class MPB_SceneProperties(PropertyGroup):
    bool_operation_prop: EnumProperty(
        name=pgettext("Operation"),
        items=[
            ('DIFFERENCE', pgettext("Difference"), pgettext("Cuts the cutter from the base")),
            ('INTERSECT', pgettext("Intersect"), pgettext("Keeps the common part of the base and cutter")),
        ],
        default='DIFFERENCE'
    )
    internal_processed_base_part_names: StringProperty(default="")

def register_scene_properties():
    bpy.utils.register_class(MPB_SceneProperties)
    Scene.mpb_props = PointerProperty(type=MPB_SceneProperties)

def unregister_scene_properties():
    del Scene.mpb_props
    bpy.utils.unregister_class(MPB_SceneProperties)

# --- 内部処理用オペレータ ---
class _OBJECT_OT_boolean_per_loose_part_internal(Operator):
    bl_idname = "object._boolean_per_loose_part_internal"
    bl_label = pgettext("Add Boolean Modifiers per Part (Internal)")

    bool_operation_str: StringProperty()
    base_obj_name_str: StringProperty()
    cutter_obj_name_str: StringProperty()
    result_collection_name_str: StringProperty()

    def _split_object_and_collect_parts(self, context, obj_to_split_original, result_collection, source_obj_suffix, part_prefix_for_report):
        bpy.ops.object.select_all(action='DESELECT')
        obj_to_split_original.select_set(True)
        context.view_layer.objects.active = obj_to_split_original
        bpy.ops.object.duplicate()
        dup_for_split = context.active_object
        dup_for_split.name = obj_to_split_original.name + source_obj_suffix

        current_collections = list(dup_for_split.users_collection)
        for coll in current_collections:
            coll.objects.unlink(dup_for_split)
        if result_collection.name not in [c.name for c in dup_for_split.users_collection]:
            result_collection.objects.link(dup_for_split)

        bpy.ops.object.select_all(action='DESELECT')
        dup_for_split.select_set(True)
        context.view_layer.objects.active = dup_for_split
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        selected_after_split = context.selected_objects[:]
        parts_list = []
        if not selected_after_split:
            if dup_for_split.name in bpy.data.objects:
                bm_check = bmesh.new(); bm_check.from_mesh(dup_for_split.data); is_valid = len(bm_check.verts)>0; bm_check.free()
                if is_valid: parts_list.append(dup_for_split)
                else: bpy.data.objects.remove(dup_for_split, do_unlink=True)

        elif len(selected_after_split) == 1 and selected_after_split[0].name.startswith(dup_for_split.name.split('.')[0]):
            single_part = selected_after_split[0]
            if single_part.name in context.view_layer.objects:
                bm_check = bmesh.new(); bm_check.from_mesh(single_part.data); is_valid = len(bm_check.verts)>0; bm_check.free()
                if is_valid:
                    parts_list.append(single_part)
                    if dup_for_split.name != single_part.name and dup_for_split.name in bpy.data.objects:
                        bm_dup_check = bmesh.new(); bm_dup_check.from_mesh(dup_for_split.data)
                        if len(bm_dup_check.verts) == 0: bpy.data.objects.remove(dup_for_split, do_unlink=True)
                        bm_dup_check.free()
                else:
                    if single_part.name in bpy.data.objects: bpy.data.objects.remove(single_part, do_unlink=True)
                    if dup_for_split.name != single_part.name and dup_for_split.name in bpy.data.objects:
                         bpy.data.objects.remove(dup_for_split, do_unlink=True)
        else:
            for part_obj in selected_after_split:
                if part_obj.type == 'MESH':
                    bm_check = bmesh.new(); bm_check.from_mesh(part_obj.data)
                    is_valid_geom = len(bm_check.verts) > 0 and len(bm_check.edges) > 0 and len(bm_check.faces) > 0
                    bm_check.free()
                    if is_valid_geom:
                        parts_list.append(part_obj)
                        current_part_collections = list(part_obj.users_collection)
                        for c in current_part_collections:
                            if c.name != result_collection.name: c.objects.unlink(part_obj)
                        if result_collection.name not in [c.name for c in part_obj.users_collection]:
                            result_collection.objects.link(part_obj)
                    else:
                        if part_obj.name in bpy.data.objects: bpy.data.objects.remove(part_obj, do_unlink=True)
            if dup_for_split.name in bpy.data.objects:
                is_dup_processed = any(p.name == dup_for_split.name for p in parts_list)
                if not is_dup_processed:
                    bm_dup_check = bmesh.new(); bm_dup_check.from_mesh(dup_for_split.data)
                    if len(bm_dup_check.verts) == 0: bpy.data.objects.remove(dup_for_split, do_unlink=True)
                    bm_dup_check.free()
        
        final_parts_list = []
        for p in parts_list:
            if p.name in context.view_layer.objects:
                if result_collection.name not in [c.name for c in p.users_collection]:
                    result_collection.objects.link(p)
                final_parts_list.append(p)
        return final_parts_list

    def execute(self, context):
        bool_operation = self.bool_operation_str
        try:
            base_obj_original = bpy.data.objects[self.base_obj_name_str]
            cutter_obj_original = bpy.data.objects[self.cutter_obj_name_str]
            result_collection = bpy.data.collections[self.result_collection_name_str]
        except KeyError as e:
            self.report({'ERROR'}, pgettext("Internal Error: Could not find object or collection - {error}").format(error=e))
            return {'CANCELLED'}

        base_parts = self._split_object_and_collect_parts(context, base_obj_original, result_collection, "_BaseSplitSource_ForBoth", "ベース")
        if not base_parts:
            self.report({'ERROR'}, pgettext("No valid base parts were created.")); return {'CANCELLED'}
        
        context.scene.mpb_props.internal_processed_base_part_names = json.dumps([p.name for p in base_parts])

        cutter_parts = self._split_object_and_collect_parts(context, cutter_obj_original, result_collection, "_CutterSplitSource_ForBoth", "カッター")
        if not cutter_parts:
            bpy.ops.object.select_all(action='DESELECT')
            for bp_obj in base_parts:
                if bp_obj.name in bpy.data.objects: bpy.data.objects[bp_obj.name].select_set(True)
            if any(obj.select_get() for obj in context.selectable_objects): bpy.ops.object.delete()
            context.scene.mpb_props.internal_processed_base_part_names = ""
            self.report({'ERROR'}, pgettext("No valid cutter parts were created.")); return {'CANCELLED'}

        total_mods_added = 0
        for base_part_obj in base_parts:
            if base_part_obj.name not in context.view_layer.objects: continue
            for cutter_part_obj in cutter_parts:
                if cutter_part_obj.name not in context.view_layer.objects: continue
                mod_name = f"Boolean_{cutter_part_obj.name}_on_{base_part_obj.name}"
                mod = base_part_obj.modifiers.new(name=mod_name, type='BOOLEAN')
                mod.operation = bool_operation; mod.object = cutter_part_obj; mod.solver = 'EXACT'
                total_mods_added +=1
        
        for cp in cutter_parts:
            if cp.name in context.view_layer.objects:
                cp.hide_set(True); cp.hide_render = True
        return {'FINISHED'}


class _OBJECT_OT_apply_boolean_modifiers_internal(Operator):
    bl_idname = "object._apply_boolean_modifiers_internal"
    bl_label = pgettext("Apply Modifiers and Join (Internal)")

    object_names_with_modifiers_json: StringProperty()
    original_base_for_transform_name_str: StringProperty()
    result_collection_name_str: StringProperty()

    def execute(self, context):
        try:
            object_names_with_modifiers = json.loads(self.object_names_with_modifiers_json)
            original_base_for_transform = bpy.data.objects[self.original_base_for_transform_name_str]
            target_collection = bpy.data.collections[self.result_collection_name_str]
        except (json.JSONDecodeError, KeyError) as e:
            self.report({'ERROR'}, pgettext("Internal Error: Failed to load properties - {error}").format(error=e))
            return {'CANCELLED'}

        if not object_names_with_modifiers:
            self.report({'ERROR'}, pgettext("Internal Error: No target objects for apply.")); return {'CANCELLED'}

        base_location = original_base_for_transform.location.copy()
        base_rotation = original_base_for_transform.rotation_euler.copy()
        base_scale = original_base_for_transform.scale.copy()
        
        temp_name = original_base_for_transform.name
        suffix_to_remove = ""
        if temp_name.endswith("_BaseSplitSource_ForBoth"): suffix_to_remove = "_BaseSplitSource_ForBoth"
        elif temp_name.endswith("_CutterSplitSource_ForBoth"): suffix_to_remove = "_CutterSplitSource_ForBoth"
        if suffix_to_remove: temp_name = temp_name[:-len(suffix_to_remove)]
        base_original_name_stem = temp_name.split('.')[0]

        applied_count = 0
        objects_after_apply = []
        cutter_object_names_to_delete = set()

        for obj_name in object_names_with_modifiers:
            if obj_name not in context.view_layer.objects: continue
            obj = context.view_layer.objects[obj_name]
            if obj.type != 'MESH': continue

            boolean_mods_to_apply = [m for m in obj.modifiers if m.type == 'BOOLEAN' and m.name.startswith("Boolean_")]
            if not boolean_mods_to_apply:
                if obj.name in context.view_layer.objects: objects_after_apply.append(obj)
                continue

            bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); context.view_layer.objects.active = obj
            for mod in boolean_mods_to_apply:
                if mod.name not in obj.modifiers: continue
                if mod.object and mod.object.name in context.view_layer.objects:
                    cutter_object_names_to_delete.add(mod.object.name)
                try:
                    bpy.ops.object.modifier_apply(modifier=mod.name); applied_count += 1
                except RuntimeError: pass # エラーはコンソールに出るのでここでは無視
            if obj.name in context.view_layer.objects:
                objects_after_apply.append(context.view_layer.objects[obj.name])

        valid_objects_for_join = [o for o in objects_after_apply if o.name in context.view_layer.objects and o.type == 'MESH' and len(o.data.vertices) > 0]
        final_combined_obj = None

        if len(valid_objects_for_join) > 1:
            bpy.ops.object.select_all(action='DESELECT')
            active_cand = None
            for ojoin in valid_objects_for_join:
                if ojoin.name in context.view_layer.objects:
                    ojoin.select_set(True)
                    if not active_cand: active_cand = ojoin
                    if ojoin.name.startswith(base_original_name_stem + "_BaseSplitSource_ForBoth"):
                        active_cand = ojoin
            if not active_cand: self.report({'ERROR'}, pgettext("Internal Error: No valid active object for join.")); return {'CANCELLED'}
            context.view_layer.objects.active = active_cand
            try:
                bpy.ops.object.join(); final_combined_obj = context.active_object
                if not final_combined_obj: self.report({'ERROR'}, pgettext("Internal Error: Join failed (None).")); return {'CANCELLED'}
                final_combined_obj.name = base_original_name_stem + "_Combined"
                final_combined_obj.location = base_location; final_combined_obj.rotation_euler = base_rotation; final_combined_obj.scale = base_scale
                current_fc_collections = list(final_combined_obj.users_collection)
                for c in current_fc_collections: c.objects.unlink(final_combined_obj)
                if target_collection.name not in [c.name for c in final_combined_obj.users_collection]: target_collection.objects.link(final_combined_obj)
            except RuntimeError as e: self.report({'ERROR'}, pgettext("Internal Error: Join error: {error}").format(error=e)); return {'CANCELLED'}
        elif len(valid_objects_for_join) == 1:
            final_combined_obj = valid_objects_for_join[0]
            final_combined_obj.name = base_original_name_stem + "_Combined"
            final_combined_obj.location = base_location; final_combined_obj.rotation_euler = base_rotation; final_combined_obj.scale = base_scale
            current_fc_collections = list(final_combined_obj.users_collection)
            for c in current_fc_collections: c.objects.unlink(final_combined_obj)
            if target_collection.name not in [c.name for c in final_combined_obj.users_collection]: target_collection.objects.link(final_combined_obj)
        
        if cutter_object_names_to_delete:
            bpy.ops.object.select_all(action='DESELECT')
            objects_to_delete = []
            for name_del in cutter_object_names_to_delete:
                if final_combined_obj and name_del == final_combined_obj.name: continue
                if name_del in bpy.data.objects:
                    obj_del_data = bpy.data.objects[name_del]
                    if obj_del_data.name in context.view_layer.objects:
                        obj_del_view = context.view_layer.objects[obj_del_data.name]
                        obj_del_view.hide_set(False)
                        obj_del_view.select_set(True)
                        objects_to_delete.append(obj_del_view)
                    else: bpy.data.objects.remove(obj_del_data, do_unlink=True)
            if objects_to_delete: bpy.ops.object.delete()

        if final_combined_obj and final_combined_obj.name in bpy.data.objects:
            context.scene.mpb_props.internal_processed_base_part_names = final_combined_obj.name
        else:
            context.scene.mpb_props.internal_processed_base_part_names = ""
        return {'FINISHED'}


# --- UIから呼び出される一括処理オペレータ ---
class OBJECT_OT_boolean_split_and_apply_all(Operator):
    bl_idname = "object.boolean_split_and_apply_all"
    bl_label = pgettext("Batch Boolean Process")
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = pgettext("Creates a new collection and generates the result.")
    
    def execute(self, context):
        initial_selected = context.selected_objects[:]
        initial_active = context.active_object
        bool_operation = context.scene.mpb_props.bool_operation_prop

        if len(initial_selected) < 2: self.report({'ERROR'}, pgettext("Select at least two objects: a base (active) and a cutter.")); return {'CANCELLED'}
        if not initial_active: self.report({'ERROR'}, pgettext("Active object (base) is missing.")); return {'CANCELLED'}
        
        base_obj_original_ref = initial_active
        cutters_original_list = [obj for obj in initial_selected if obj != base_obj_original_ref and obj.type == 'MESH']
        if not cutters_original_list: self.report({'ERROR'}, pgettext("No valid mesh cutter selected.")); return {'CANCELLED'}
        cutter_obj_original_ref = cutters_original_list[0]

        if base_obj_original_ref.type != 'MESH' or cutter_obj_original_ref.type != 'MESH':
            self.report({'ERROR'}, pgettext("Base and cutter must both be mesh objects.")); return {'CANCELLED'}

        base_obj_name = base_obj_original_ref.name
        cutter_obj_name = cutter_obj_original_ref.name

        # ★★★ 結果コレクション名の生成ロジックを変更 ★★★
        base_collection_name_stem = "MultiPartBoolean_Result"
        counter = 1
        # 3桁の連番で開始 (例: _001)。必要に応じて :02d (2桁) などに変更可能
        final_collection_name_to_create = f"{base_collection_name_stem}_{counter:03d}" 

        # 既存のコレクション名と衝突しないようにカウンターを増やす
        while final_collection_name_to_create in bpy.data.collections:
            counter += 1
            final_collection_name_to_create = f"{base_collection_name_stem}_{counter:03d}"
        
        result_collection = bpy.data.collections.new(final_collection_name_to_create)
        context.view_layer.layer_collection.collection.children.link(result_collection)
        print(f"Created new result collection: '{result_collection.name}'") # コンソールへのログ出力
        
        status_mod_add = bpy.ops.object._boolean_per_loose_part_internal(
            bool_operation_str=bool_operation,
            base_obj_name_str=base_obj_name,
            cutter_obj_name_str=cutter_obj_name,
            result_collection_name_str=result_collection.name
        )
        
        if 'CANCELLED' in status_mod_add or 'ERROR' in status_mod_add:
            self.report({'ERROR'}, pgettext("Error during part-wise boolean addition."))
            if result_collection.name in bpy.data.collections:
                 if not result_collection.objects: bpy.data.collections.remove(result_collection)
            return {'CANCELLED'}
        
        try:
            processed_base_part_names_json = context.scene.mpb_props.internal_processed_base_part_names
            if not processed_base_part_names_json: raise ValueError("processed_base_part_names is empty")
            objects_with_modifiers_names = json.loads(processed_base_part_names_json)
            if not isinstance(objects_with_modifiers_names, list) or not all(isinstance(name, str) for name in objects_with_modifiers_names):
                raise TypeError("Decoded JSON is not a list of strings")
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            self.report({'ERROR'}, pgettext("Could not retrieve list of objects with boolean modifiers: {error}").format(error=e))
            if result_collection.name in bpy.data.collections:
                 if not result_collection.objects: bpy.data.collections.remove(result_collection)
            return {'CANCELLED'}

        if not objects_with_modifiers_names:
            self.report({'ERROR'}, pgettext("No objects with boolean modifiers found (list is empty)."))
            if result_collection.name in bpy.data.collections:
                 if not result_collection.objects: bpy.data.collections.remove(result_collection)
            return {'CANCELLED'}

        status_apply = bpy.ops.object._apply_boolean_modifiers_internal(
            object_names_with_modifiers_json=json.dumps(objects_with_modifiers_names),
            original_base_for_transform_name_str=base_obj_name,
            result_collection_name_str=result_collection.name
        )

        if 'CANCELLED' in status_apply or 'ERROR' in status_apply:
            self.report({'ERROR'}, pgettext("Error during modifier application and join process."))
            return {'CANCELLED'}

        final_combined_obj_name_from_prop = context.scene.mpb_props.internal_processed_base_part_names
        
        if final_combined_obj_name_from_prop:
            self.report({'INFO'}, pgettext("Batch boolean process completed. Result: '{result_name}' in collection '{coll_name}'").format(result_name=final_combined_obj_name_from_prop, coll_name=result_collection.name))
        else:
            self.report({'WARNING'}, pgettext("Batch boolean process completed. Result: Unknown in collection '{coll_name}'").format(coll_name=result_collection.name))
        
        if final_combined_obj_name_from_prop and final_combined_obj_name_from_prop in context.view_layer.objects:
            bpy.ops.object.select_all(action='DESELECT')
            final_obj = context.view_layer.objects[final_combined_obj_name_from_prop]
            final_obj.select_set(True)
            context.view_layer.objects.active = final_obj
            
        return {'FINISHED'}
        
# --- UIパネル定義 ---
class VIEW3D_PT_multi_part_boolean_panel(Panel): # クラス名も変更
    bl_label = pgettext("Multi-Part Boolean") # パネルのタイトルも翻訳
    bl_idname = "VIEW3D_PT_multi_part_boolean_panel" # IDも変更
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Multi-Part Boolean" # UIタブ名も英語ベースに (翻訳辞書で日本語化)

    def draw(self, context):
        layout = self.layout
        props = context.scene.mpb_props # PropertyGroupからプロパティを取得

        layout.label(text=pgettext("1. Object Selection and Settings:"))
        layout.prop(props, "bool_operation_prop") # text="" でプロパティ自身のnameを使う
        
        layout.separator()
        layout.label(text=pgettext("2. Execute Process:"))
        layout.operator(OBJECT_OT_boolean_split_and_apply_all.bl_idname, text=pgettext("Execute Batch Boolean Process"))


# --- 登録/解除処理 ---
classes = (
    MPB_SceneProperties, # PropertyGroupを登録
    _OBJECT_OT_boolean_per_loose_part_internal,
    _OBJECT_OT_apply_boolean_modifiers_internal,
    OBJECT_OT_boolean_split_and_apply_all,
    VIEW3D_PT_multi_part_boolean_panel, # パネルクラス名変更を反映
)
def register():
    # 翻訳の登録
    try:
        bpy.app.translations.register(__name__, translations_dict)
    except ValueError as e:
        if "already registered" not in str(e):
            raise e
        print(f"Translations for '{bl_info['name']}' already registered, skipping.")

    # プロパティとクラスの登録
    try:
        register_scene_properties()  # PropertyGroupを登録
        for cls in classes:
            try:
                bpy.utils.register_class(cls)
            except ValueError as e:
                if "already registered" not in str(e):
                    raise e
                print(f"Class '{cls.__name__}' already registered, skipping.")
        print(f"Addon '{bl_info['name']}' version {bl_info['version']} registered.")
    except Exception as e:
        print(f"Error during registration: {e}")
        unregister()  # 失敗したらクリーンアップ
        raise e

def unregister():
    # 翻訳の登録解除
    try:
        bpy.app.translations.unregister(__name__)
    except ValueError as e:
        if "not registered" not in str(e):
            raise e
        print(f"Translations for '{bl_info['name']}' not registered, skipping.")

    # クラスの登録解除
    for cls in reversed(classes):
        try:
            if hasattr(bpy.types, cls.bl_idname):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering class '{cls.__name__}': {e}")

    # プロパティの登録解除
    try:
        unregister_scene_properties()
    except Exception as e:
        print(f"Error unregistering scene properties: {e}")

if __name__ == "__main__":
    # テスト用に、既存の登録をすべて解除してから再登録
    try:
        unregister()  # 既存の登録を解除
    except Exception as e:
        print(f"Error during initial unregister: {e}")

    # 再登録
    try:
        register()
    except Exception as e:
        print(f"Error during re-registration: {e}")
