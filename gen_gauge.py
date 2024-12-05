import omni.replicator.core as rep
import omni.usd as usd
import datetime
import asyncio
import json
import os
from typing import Union
from pxr import Usd, Sdf

GROUND_PATH='omniverse://localhost/NVIDIA/Assets/Isaac/4.2/Isaac/Environments/Terrains/flat_plane.usd'
GAUGE_PATH='omniverse://localhost/Library/Pressure Gauge 2.usd'
NOW=datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
OUTPUT_DIR = "/home/ifodor/Downloads/data/gauge_data_basic_"+NOW


def normalize_rotation(rotation):
    rotation = -rotation
    return (rotation - (-135)) / 270 * 1.0

def get_current_stage() -> Usd.Stage:
    return usd.get_context().get_stage()

def get_attribute_value(prim: Usd.Prim, attribute_name: str):
    attr = prim.GetAttribute(attribute_name)
    return attr.Get()

def get_prim_by_path(stage: Usd.Stage, prim_path: Union[str, Sdf.Path]) -> Usd.Prim:
    return stage.GetPrimAtPath(prim_path)

def uniform_random_rotation(prim, min_x = 0, min_y = 0, min_z = 0, max_x = 0, max_y = 0, max_z = 0):
    with prim:
        rotation = rep.distribution.uniform((min_x, min_y, min_z), (max_x, max_y, max_z))
        rep.modify.pose(rotation = rotation)


with rep.new_layer() as layer:
    stage = usd.get_context().get_stage()
    #rep.settings.carb_settings("/omni/replicator/RTSubframes", 20)
    ground = rep.create.from_usd(GROUND_PATH)
    gauge = rep.create.from_usd(GAUGE_PATH)
    
    camera =  rep.create.camera()

    with camera:
        rep.modify.pose(look_at = (0,0,1))

    render_product = rep.create.render_product(camera, resolution=(2048, 2048))
    
    with ground:
      rep.physics.collider()
      
    with gauge:
      rep.physics.collider()
      rep.modify.pose(position=(0,0,1), rotation = (0,0,180))
      rep.modify.semantics([('class', "gauge")])
      rep.modify.pose(size = 5)
    	
    
    hand = rep.get.prim_at_path("/Replicator/Ref_Xform_01/Ref/Pressure_Gauge/Pressure_Gauge_uw_obj/Metal/Hand")
    with hand:
        rep.modify.semantics([('class', "gauge_needle")])

    rep.randomizer.register(uniform_random_rotation)
    with rep.trigger.on_frame(num_frames=40):
        uniform_random_rotation(hand, min_z = -135, max_z = 135)

        with camera:
             rep.modify.pose(position=rep.distribution.uniform((-10, -20, 10), (10, 0, 30)), look_at=rep.distribution.uniform((0,-3,1), (0,-3,1)))
    
    
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize( output_dir=OUTPUT_DIR, rgb=True, bounding_box_2d_tight=True, semantic_types=["class"])
    writer.attach([render_product])
    

async def run():

    rotations = []
    rotations_filename = "rotations.json"
    stage = get_current_stage()
    # This is the main render loop that renders 20 frames.
    for i in range(0,20):
        # This renders one new frame (the subframes are needed for high quality raytracing)
        await rep.orchestrator.step_async(rt_subframes=20)
        
        # Access a prim when the simulation is not running and read it's rotation.
        prim = get_prim_by_path(stage, "/Replicator/Ref_Xform_01/Ref/Pressure_Gauge/Pressure_Gauge_uw_obj/Metal/Hand")
        rotation = get_attribute_value(prim, "xformOp:rotateXYZ")
        rotation_norm = normalize_rotation(rotation[2])
        rotations.append({"frame" : i, "rotation" : rotation_norm})
        print(f"Step {i}, rotation: {rotation} rotation_norm: {rotation_norm}")

    # After the render we write the rotations to file
    with open(os.path.join(OUTPUT_DIR, rotations_filename), "w") as f:
        json.dump(rotations, f, indent=2)

asyncio.ensure_future(run())