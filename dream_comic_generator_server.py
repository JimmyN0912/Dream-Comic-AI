import requests
import json
import argparse
import os
import io
import base64
from PIL import Image
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from groq import Groq
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import uuid

load_dotenv()

app = Flask(__name__)

# Configure upload folder for images
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# AI Endpoint configurations
TEXT_GEN_URL = "http://localhost:5001"
STABLE_DIFFUSION_URL = "http://localhost:7861"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

def translate_to_traditional_chinese(text: str) -> str:
    """
    Translate text to Traditional Chinese using the Groq API
    
    Args:
        text: Text to translate
        
    Returns:
        Translated text in Traditional Chinese
    """
    prompt = f"Translate the following text to Traditional Chinese:\n{text}"
    
    try:
        print(f"Sending translation request for: {text[:50]}...")
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
        )

        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Error during translation: {str(e)}")
        return text

def generate_dream_comic(
    dream_text: str = "",
    output_file: Optional[str] = None,
    generate_images: bool = False,
    output_dir: Optional[str] = None,
    translate_to_chinese: bool = False
) -> Dict[str, Any]:
    """
    Generate a four-panel comic based on a dream image and/or text description.
    
    Args:
        image_path: Optional path to an image file representing the dream
        dream_text: Text description of the dream
        output_file: Optional file path to save the results
        generate_images: Whether to generate images for each panel
        output_dir: Directory to save the generated images
        translate_to_chinese: Whether to translate panel descriptions to Traditional Chinese
        
    Returns:
        Dictionary containing the generated comic panels and image paths
    """
    # Prepare the messages for the API
    messages = [
        {
            "role": "system", 
            "content": "You are a creative dream interpreter and comic creator. Generate descriptions for four sequential comic panels that continue the dream narrative. Format your response with numbered panels: 'Panel 1:', 'Panel 2:', etc. Example: 'Panel 1: Male furry Lycanthrope with fur-covered body in ancient ruins, howling at the full moon, surrounded by eerie mist, werewolf transformation, elder scrolls, eslweyr, glitch aesthetic, anime-inspired, digital illustration, artstation, furry' The generated prompt show not include any moving elements or dialogue."
        },
        {
            "role": "user", 
            "content": f"I had this dream: {dream_text}\n\nPlease create four sequential comic panels that continue this dream narrative. For each panel, provide a clear, detailed description of what should be depicted."
        }
    ]
    
    files = {}
    # Add image if provided
    if image_path and os.path.exists(image_path):
        files = {"image": open(image_path, "rb")}
        print(f"Including dream image: {image_path}")
    
    try:
        # Call the combined analysis endpoint as it handles both image and text
        # Updated to match the API expectations
        response = requests.post(
            url = f"{TEXT_GEN_URL}/v1/chat/completions",
            json= {
                "mode": "instruct", 
                "stream": "false",
                "messages": messages,
            }
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return {"error": response.text}
        
        print("Dream comic description generation complete.")
        result = response.json()
        
        
        # Check different possible response structures
        if "choices" in result and len(result["choices"]) > 0:
            if "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                content = result["choices"][0]["message"]["content"]
            else:
                content = result["choices"][0].get("content", "")
        elif "content" in result:
            content = result["content"]
        else:
            # If we can't find the content in expected places, use the whole result as a string
            content = str(result)
            print("Warning: Unexpected response format. Using full response as content.")
        
        # Extract panel descriptions from the generated content
        print("\nExtracting panel descriptions from response...")
        comic_panels = extract_panels(content)
        print("Panel extraction complete.")
        
        # Generate images for each panel if requested
        if generate_images:
            if not output_dir:
                output_dir = os.path.dirname(output_file) if output_file else "."
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Generate images for each panel
            for i in range(1, 5):
                panel_key = f"panel{i}"
                image_path = os.path.join(output_dir, f"panel_{i}.png")
                
                # Only generate if we have valid content
                if comic_panels[panel_key] and "[Panel" not in comic_panels[panel_key]:
                    print(f"Generating image for panel {i}...")
                    img_path = generate_image(comic_panels[panel_key], image_path)
                    if img_path:
                        comic_panels[f"{panel_key}_image"] = img_path
                    else:
                        comic_panels[f"{panel_key}_image"] = "Failed to generate image"
                else:
                    comic_panels[f"{panel_key}_image"] = "No valid description for image generation"
        
        # Translate panel descriptions to Traditional Chinese if requested
        if translate_to_chinese:
            print("\nBeginning translation process for individual panels...")
            
            # Process each panel independently
            for i in range(1, 5):
                panel_key = f"panel{i}"
                panel_description = comic_panels[panel_key]
                
                # Skip translation if the panel description is not valid
                if not panel_description or "[Panel" in panel_description:
                    print(f"Panel {i}: No valid description found for translation")
                    comic_panels[f"{panel_key}_chinese"] = "Translation not available"
                    continue
                
                print(f"\nPanel {i} translation:")
                print(f"Original: {panel_description}")
                
                # Send this specific panel description for translation
                translated_description = translate_to_traditional_chinese(panel_description)
                comic_panels[f"{panel_key}_chinese"] = translated_description
                
                print(f"Translation complete for Panel {i}")
                print(f"Translated: {translated_description[:100]}..." if len(translated_description) > 100 else f"Translated: {translated_description}")
            
            print("\nAll panel translations completed.")
        
        # Save to output file if specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(comic_panels, f, indent=2)
            print(f"Comic panels saved to {output_file}")
        
        # Print the results
        print_comic_panels(comic_panels)
        
        return comic_panels
    
    except Exception as e:
        print(f"Error generating dream comic: {str(e)}")
        return {"error": str(e)}
    finally:
        # Close the image file if it was opened
        if files and "image" in files:
            files["image"].close()

def extract_panels(content: str) -> Dict[str, str]:
    """Extract the four panels from the AI-generated content"""
    panels = {}
    
    # Simple parsing - look for Panel 1, Panel 2, etc.
    lines = content.split("\n")
    current_panel = None
    
    for line in lines:
        if "Panel 1:" in line or "Panel 1" in line:
            current_panel = "panel1"
            panels[current_panel] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif "Panel 2:" in line or "Panel 2" in line:
            current_panel = "panel2"
            panels[current_panel] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif "Panel 3:" in line or "Panel 3" in line:
            current_panel = "panel3"
            panels[current_panel] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif "Panel 4:" in line or "Panel 4" in line:
            current_panel = "panel4"
            panels[current_panel] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif current_panel and line.strip():
            # Append content to current panel
            panels[current_panel] += " " + line.strip()
    
    # Ensure we have all four panels
    for i in range(1, 5):
        panel_key = f"panel{i}"
        if panel_key not in panels:
            panels[panel_key] = f"[Panel {i} description not found]"
    
    return panels

def generate_image(prompt: str, output_path: str, steps: int = 20) -> Optional[str]:
    """
    Generate an image from a text prompt using Stable Diffusion API
    
    Args:
        prompt: Text description to generate image from
        output_path: Path to save the generated image
        steps: Number of inference steps (higher = more detail but slower)
        
    Returns:
        Path to the saved image or None if generation failed
    """
    payload = {
        "prompt": prompt,
        "steps": steps
    }
    
    try:
        response = requests.post(url=f'{STABLE_DIFFUSION_URL}/sdapi/v1/txt2img', json=payload)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        r = response.json()
        
        image = Image.open(io.BytesIO(base64.b64decode(r['images'][0])))
        image.save(output_path)
        
        print(f"Image saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None

def print_comic_panels(panels: Dict[str, str]) -> None:
    """Pretty print the comic panels"""
    print("\n" + "="*50)
    print(" "*20 + "DREAM COMIC")
    print("="*50)
    
    for i in range(1, 5):
        panel_key = f"panel{i}"
        image_key = f"{panel_key}_image"
        chinese_key = f"{panel_key}_chinese"
        
        print(f"\nPANEL {i}:")
        print("-"*50)
        print(panels[panel_key])
        
        # Print Chinese translation if available
        if chinese_key in panels:
            print("\nTraditional Chinese:")
            print(panels[chinese_key])
        
        # Print image path if available
        if image_key in panels:
            print(f"\nImage: {panels[image_key]}")
    
    print("\n" + "="*50 + "\n")

# New API endpoint
@app.route('/api/generate-comic', methods=['POST'])
def api_generate_comic():
    """
    API endpoint for generating comics from dream descriptions
    
    Expected request parameters:
    - dream_text: String description of the dream
    - image: Optional image file to include with the dream
    - generate_images: Boolean indicating whether to generate images (default: False)
    - translate_to_chinese: Boolean indicating whether to translate to Chinese (default: False)
    """
    try:
        # Check where the data is coming from (JSON or form)
        if request.is_json:
            print(f"New JSON request received: {request.json}")
            data = request.json
        else:
            print(f"New form request received: {request.form}")
            data = request.form.to_dict()
        
        # Get dream text (required)
        dream_text = data.get('dream_text') or data.get('prompt')
        if not dream_text:
            return jsonify({'error': 'Missing required parameter: dream_text'}), 400
            
        # Process image if provided
        image_path = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                # Create a unique filename
                filename = secure_filename(f"{uuid.uuid4()}_{image_file.filename}")
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
        
        # Create unique output directory for this request
        session_id = str(uuid.uuid4())
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        os.makedirs(output_dir, exist_ok=True)

        #Print uuid
        print(f"New request received, session id: {session_id}")
        
        # Generate the comic
        comic_result = generate_dream_comic(
            dream_text=dream_text,
            output_file=None,  # Don't save to file since we're returning via API
            generate_images=True, # Always generate images for API response
            output_dir=output_dir,
            translate_to_chinese=True # Always translate to Chinese for API response
        )
        
        # Process result for API response
        response_data = {
            'panels': {},
            'session_id': session_id
        }
        
        # Process each panel for the response
        for i in range(1, 5):
            panel_key = f"panel{i}"
            panel_data = {
                'description': comic_result.get(panel_key, f"[Panel {i} description not found]")
            }
            
            # Add Chinese translation if available
            chinese_key = f"{panel_key}_chinese"
            if chinese_key in comic_result:
                panel_data['chinese'] = comic_result[chinese_key]
                
            # Add image info if available
            image_key = f"{panel_key}_image"
            if image_key in comic_result and os.path.exists(comic_result[image_key]):
                image_filename = os.path.basename(comic_result[image_key])
                panel_data['image_url'] = f"/api/images/{session_id}/{image_filename}"
                
            response_data['panels'][panel_key] = panel_data
            
        # Return the response
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to serve generated images
@app.route('/api/images/<session_id>/<filename>')
def serve_image(session_id, filename):
    """Serve generated images"""
    directory = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    return send_from_directory(directory, filename)

def main():
    """Main function to run the script from command line"""
    parser = argparse.ArgumentParser(description="Dream Comic Generator")
    parser.add_argument("--text", type=str, help="Description of the dream")
    parser.add_argument("--output", type=str, help="Output file path to save results")
    parser.add_argument("--generate-images", action="store_true", help="Generate images for each panel")
    parser.add_argument("--output-dir", type=str, help="Directory to save generated images")
    parser.add_argument("--translate", action="store_true", help="Translate panel descriptions to Traditional Chinese")
    parser.add_argument("--server", action="store_true", help="Run as a Flask API server")
    parser.add_argument("--port", type=int, default=5000, help="Port for the Flask API server")
    
    args = parser.parse_args()
    
    if args.server:
        # Run as a Flask API server
        app.run(host='0.0.0.0', port=args.port, debug=False)
    elif args.text:
        # Run in CLI mode with the provided arguments
        generate_dream_comic(
            dream_text=args.text,
            output_file=args.output,
            generate_images=args.generate_images,
            output_dir=args.output_dir,
            translate_to_chinese=args.translate
        )
    else:
        print("Error: Either --server or --text must be provided")
        parser.print_help()

if __name__ == "__main__":
    main()
