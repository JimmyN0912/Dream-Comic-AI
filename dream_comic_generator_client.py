import requests
import io
from PIL import Image
import os
import streamlit as st
import json
import datetime
from pathlib import Path
import shutil

# Variables
url = "https://api.jimmyn.idv.tw"

# Initialize session state to track view mode
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'new'
if 'selected_session' not in st.session_state:
    st.session_state.selected_session = None
if 'refresh_history' not in st.session_state:
    st.session_state.refresh_history = False

# Set wide mode as default
st.set_page_config(layout="wide")

# Add custom CSS for fixed-height description containers
st.markdown("""
<style>
    .fixed-height-container {
        height: 150px;
        overflow-y: auto;
        margin-bottom: 10px;
        background-color: rgba(240, 240, 240, 0.3);
        padding: 8px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Function to create fixed-height description container
def fixed_height_container(text):
    st.markdown(f'<div class="fixed-height-container">{text}</div>', unsafe_allow_html=True)

# Function to save generation metadata
def save_generation_metadata(session_id, prompt, response_data):
    save_dir = Path(__file__).parent / "dream_comics" / session_id
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Create metadata with timestamp and prompt
    metadata = {
        'session_id': session_id,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'prompt': prompt,
        'response_data': response_data
    }
    
    # Save metadata to JSON file
    with open(save_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=4)

# Function to delete a specific session
def delete_session(session_id):
    try:
        session_dir = Path(__file__).parent / "dream_comics" / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
            st.session_state.refresh_history = True
            # Reset selected session if it was deleted
            if (st.session_state.selected_session and 
                st.session_state.selected_session.get('session_id') == session_id):
                st.session_state.selected_session = None
                st.session_state.view_mode = 'new'
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting session: {e}")
        return False

# Function to delete all history
def delete_all_history():
    try:
        dream_comics_dir = Path(__file__).parent / "dream_comics"
        if dream_comics_dir.exists():
            for item in dream_comics_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
            st.session_state.refresh_history = True
            st.session_state.selected_session = None
            st.session_state.view_mode = 'new'
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting all history: {e}")
        return False

# Function to get list of previous generations
def get_previous_generations():
    dream_comics_dir = Path(__file__).parent / "dream_comics"
    if not dream_comics_dir.exists():
        return []
    
    generations = []
    for session_dir in dream_comics_dir.iterdir():
        if not session_dir.is_dir():
            continue
        
        metadata_file = session_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                generations.append(metadata)
            except:
                # Skip if metadata can't be loaded
                pass
    
    # Sort by timestamp, newest first
    generations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return generations

# Function to display a comic from stored metadata
def display_comic_from_metadata(metadata):
    st.subheader("DREAM COMIC")
    st.write(f"Session ID: {metadata['session_id']}")
    st.write(f"Generated on: {metadata['timestamp']}")
    st.write(f"Prompt: {metadata['prompt']}")
    st.markdown("---")
    
    # Get response data from metadata
    response_data = metadata['response_data']
    session_id = metadata['session_id']
    
    # Create a 2x2 grid layout for panels
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    
    # Panel 1 (top-left)
    with row1_col1:
        st.subheader("Panel 1")
        st.markdown("**Description:**")
        fixed_height_container(response_data['panels']['panel1']['description'])
        st.markdown("**Chinese Description:**")
        fixed_height_container(response_data['panels']['panel1']['chinese'])
        display_image_from_url(response_data['panels']['panel1']['image_url'], 1, session_id)
    
    # Display panels 2-4 similarly
    with row1_col2:
        st.subheader("Panel 2")
        st.markdown("**Description:**")
        fixed_height_container(response_data['panels']['panel2']['description'])
        st.markdown("**Chinese Description:**")
        fixed_height_container(response_data['panels']['panel2']['chinese'])
        display_image_from_url(response_data['panels']['panel2']['image_url'], 2, session_id)
    
    with row2_col1:
        st.subheader("Panel 3")
        st.markdown("**Description:**")
        fixed_height_container(response_data['panels']['panel3']['description'])
        st.markdown("**Chinese Description:**")
        fixed_height_container(response_data['panels']['panel3']['chinese'])
        display_image_from_url(response_data['panels']['panel3']['image_url'], 3, session_id)
    
    with row2_col2:
        st.subheader("Panel 4")
        st.markdown("**Description:**")
        fixed_height_container(response_data['panels']['panel4']['description'])
        st.markdown("**Chinese Description:**")
        fixed_height_container(response_data['panels']['panel4']['chinese'])
        display_image_from_url(response_data['panels']['panel4']['image_url'], 4, session_id)

# Function to display image from URL or local file
def display_image_from_url(image_url, panel_num, session_id):
    try:
        # Check if image exists locally first
        save_dir = Path(__file__).parent / "dream_comics" / session_id
        local_path = save_dir / f"panel_{panel_num}.png"
        
        if local_path.exists():
            # Load the saved image
            image = Image.open(local_path)
            st.image(image, caption=f"Panel {panel_num}", use_container_width=True)
            return True
        
        # If not local, get the image from URL
        response = requests.get(f"{url}{image_url}")
        if response.status_code == 200:
            # Create an image from the response content
            image = Image.open(io.BytesIO(response.content))
            
            # Save the image
            save_dir.mkdir(parents=True, exist_ok=True)
            image.save(local_path)
            
            # Display the image
            st.image(image, caption=f"Panel {panel_num}", use_container_width=True)
            return True
        else:
            st.error(f"Failed to fetch image {panel_num}. Status code: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error displaying image {panel_num}: {e}")
        return False

# Add sidebar for navigation
st.sidebar.title("Dream Comic Navigator")

# Button to generate new comics
if st.sidebar.button("Create New Comic"):
    st.session_state.view_mode = 'new'
    st.session_state.selected_session = None

# Display history section in sidebar
st.sidebar.subheader("History")

# Delete all history button
delete_all_col1, delete_all_col2 = st.sidebar.columns([3, 1])
with delete_all_col1:
    st.write("Delete all history:")
    st.write("刪除所有歷史記錄->")
with delete_all_col2:
    if st.button("🗑️ All", help="Delete all history"):
        if delete_all_history():
            st.sidebar.success("All history deleted")
            st.session_state.refresh_history = True

# Get and display previous generations
previous_generations = get_previous_generations()
if not previous_generations:
    st.sidebar.text("No previous generations found")
else:
    # Force refresh if needed
    if st.session_state.refresh_history:
        st.session_state.refresh_history = False
        st.experimental_rerun()
        
    # Display history items with delete buttons
    for idx, gen in enumerate(previous_generations):
        session_id = gen.get('session_id', '')
        timestamp = gen.get('timestamp', 'Unknown date')
        prompt_preview = gen.get('prompt', '')[:30] + '...' if len(gen.get('prompt', '')) > 30 else gen.get('prompt', '')
        
        col1, col2 = st.sidebar.columns([4, 1])
        
        # View button
        with col1:
            if st.button(f"{timestamp}: {prompt_preview}", key=f"history_{idx}"):
                st.session_state.view_mode = 'history'
                st.session_state.selected_session = gen
        
        # Delete button
        with col2:
            if st.button("🗑️", key=f"delete_{idx}", help=f"Delete this entry"):
                if delete_session(session_id):
                    st.sidebar.success(f"Deleted session {session_id}")
                    st.session_state.refresh_history = True
                    st.experimental_rerun()

# Main content area
if st.session_state.view_mode == 'history' and st.session_state.selected_session:
    # Display selected comic from history
    display_comic_from_metadata(st.session_state.selected_session)
    
    # Add delete button for current view
    if st.button("Delete This Comic"):
        session_id = st.session_state.selected_session.get('session_id')
        if delete_session(session_id):
            st.success(f"Deleted session {session_id}")
            st.session_state.refresh_history = True
            st.experimental_rerun()
else:
    # Default view - new comic generation
    st.title("Dream Comic Generator")
    st.write("Enter your dream description below and click the button to generate a comic. 在下方輸入您的夢境描述，然後點擊按鈕生成漫畫。")

    # User input via Streamlit
    prompt = st.text_area("Enter your dream text: 輸入您的夢境描述：", height=100)

    # Generate comic when button is clicked
    if st.button("Generate Comic"):
        if prompt:
            with st.spinner("Generating your dream comic... This may take a minute..."):
                data = {'dream_text': prompt}

                try:
                    response = requests.post(f"{url}/api/generate-comic", data=data, timeout=600)

                    # Parse and display the response
                    response_data = response.json()
                    
                    # Store session_id for image saving
                    session_id = response_data['session_id']
                    
                    # Save metadata for this generation
                    save_generation_metadata(session_id, prompt, response_data)
                    
                    st.subheader("DREAM COMIC GENERATION RESULTS")
                    st.write(f"Session ID: {response_data['session_id']}")
                    st.markdown("---")

                    # Create a 2x2 grid layout for panels
                    row1_col1, row1_col2 = st.columns(2)
                    row2_col1, row2_col2 = st.columns(2)
                    
                    # Panel 1 (top-left)
                    with row1_col1:
                        st.subheader("Panel 1")
                        st.markdown("**Description:**")
                        fixed_height_container(response_data['panels']['panel1']['description'])
                        st.markdown("**Chinese Description:**")
                        fixed_height_container(response_data['panels']['panel1']['chinese'])
                        image_url = response_data['panels']['panel1']['image_url']
                        display_image_from_url(image_url, 1, session_id)
                    
                    # Panel 2 (top-right)
                    with row1_col2:
                        st.subheader("Panel 2")
                        st.markdown("**Description:**")
                        fixed_height_container(response_data['panels']['panel2']['description'])
                        st.markdown("**Chinese Description:**")
                        fixed_height_container(response_data['panels']['panel2']['chinese'])
                        image_url = response_data['panels']['panel2']['image_url']
                        display_image_from_url(image_url, 2, session_id)
                    
                    # Panel 3 (bottom-left)
                    with row2_col1:
                        st.subheader("Panel 3")
                        st.markdown("**Description:**")
                        fixed_height_container(response_data['panels']['panel3']['description'])
                        st.markdown("**Chinese Description:**")
                        fixed_height_container(response_data['panels']['panel3']['chinese'])
                        image_url = response_data['panels']['panel3']['image_url']
                        display_image_from_url(image_url, 3, session_id)
                    
                    # Panel 4 (bottom-right)
                    with row2_col2:
                        st.subheader("Panel 4")
                        st.markdown("**Description:**")
                        fixed_height_container(response_data['panels']['panel4']['description'])
                        st.markdown("**Chinese Description:**")
                        fixed_height_container(response_data['panels']['panel4']['chinese'])
                        image_url = response_data['panels']['panel4']['image_url']
                        display_image_from_url(image_url, 4, session_id)

                    st.markdown("---")
                    save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dream_comics', session_id))
                    st.success(f"All images saved to: {save_path}")
                
                except requests.exceptions.Timeout:
                    st.error("Request timed out. The server took too long to respond.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter your dream text first.")
