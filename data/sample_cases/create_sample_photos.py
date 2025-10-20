"""
Script to generate sample photo placeholders for test cases.
Creates simple placeholder images with labels for testing.
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_placeholder_image(filename, text, size=(800, 600), bg_color=(200, 200, 200)):
    """Create a placeholder image with text"""
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a larger font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 40)
        small_font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw text in center
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size[0] - text_width) / 2, (size[1] - text_height) / 2)
    
    draw.text(position, text, fill=(50, 50, 50), font=font)
    
    # Add watermark
    watermark = "Sample Photo for Testing"
    wm_bbox = draw.textbbox((0, 0), watermark, font=small_font)
    wm_width = wm_bbox[2] - wm_bbox[0]
    wm_position = ((size[0] - wm_width) / 2, size[1] - 40)
    draw.text(wm_position, watermark, fill=(100, 100, 100), font=small_font)
    
    img.save(filename, 'JPEG', quality=85)
    print(f"Created {filename}")


def create_case_a_photos():
    """Create photos for Case A - Burst Pipe"""
    os.makedirs("case_a", exist_ok=True)
    
    create_placeholder_image(
        "case_a/photo_1_bathroom_flooding.jpg",
        "Bathroom Water Damage",
        bg_color=(180, 200, 220)
    )
    
    create_placeholder_image(
        "case_a/photo_2_burst_pipe.jpg",
        "Burst Pipe Behind Wall",
        bg_color=(160, 180, 200)
    )
    
    create_placeholder_image(
        "case_a/photo_3_kitchen_ceiling.jpg",
        "Kitchen Ceiling Damage",
        bg_color=(190, 190, 170)
    )
    
    create_placeholder_image(
        "case_a/photo_4_water_damage_closeup.jpg",
        "Water Damage Close-up",
        bg_color=(170, 180, 190)
    )


def create_case_b_photos():
    """Create photos for Case B - Seepage"""
    os.makedirs("case_b", exist_ok=True)
    
    create_placeholder_image(
        "case_b/photo_1_wall_staining.jpg",
        "Basement Wall Staining",
        bg_color=(150, 140, 130)
    )
    
    create_placeholder_image(
        "case_b/photo_2_moisture_area.jpg",
        "Moisture on Foundation",
        bg_color=(140, 150, 140)
    )
    
    create_placeholder_image(
        "case_b/photo_3_carpet_damage.jpg",
        "Carpet Moisture Damage",
        bg_color=(160, 150, 140)
    )


def create_case_c_photos():
    """Create photos for Case C - Auto Collision"""
    os.makedirs("case_c", exist_ok=True)
    
    create_placeholder_image(
        "case_c/photo_1_front_damage.jpg",
        "Front Right Quarter Panel",
        bg_color=(180, 180, 200)
    )
    
    create_placeholder_image(
        "case_c/photo_2_door_damage.jpg",
        "Passenger Door Damage",
        bg_color=(170, 170, 190)
    )
    
    create_placeholder_image(
        "case_c/photo_3_wheel_damage.jpg",
        "Wheel and Tire Damage",
        bg_color=(160, 160, 180)
    )
    
    create_placeholder_image(
        "case_c/photo_4_overall_view.jpg",
        "Overall Vehicle Damage",
        bg_color=(190, 190, 210)
    )
    
    create_placeholder_image(
        "case_c/photo_5_accident_scene.jpg",
        "Accident Scene Overview",
        bg_color=(200, 200, 200)
    )


if __name__ == "__main__":
    print("Generating sample photo placeholders...")
    print("\nCase A - Burst Pipe:")
    create_case_a_photos()
    
    print("\nCase B - Seepage:")
    create_case_b_photos()
    
    print("\nCase C - Auto Collision:")
    create_case_c_photos()
    
    print("\n✓ All photo placeholders created successfully!")
    print("\nNote: These are placeholder images for testing.")
    print("In production, real photos would be uploaded by users.")
