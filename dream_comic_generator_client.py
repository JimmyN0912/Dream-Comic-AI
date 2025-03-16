import requests
import io
from PIL import Image
import os
import streamlit as st

# Variables
url = "https://api.jimmyn.idv.tw"

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

# Function to display image from URL
def display_image_from_url(image_url, panel_num, session_id):
    try:
        # Get the image data from the URL
        response = requests.get(f"{url}{image_url}")
        if response.status_code == 200:
            # Create an image from the response content
            image = Image.open(io.BytesIO(response.content))
            
            # Optional: Save the image
            save_dir = os.path.join(os.path.dirname(__file__), "dream_comics", session_id)
            os.makedirs(save_dir, exist_ok=True)
            filename = f"panel_{panel_num}.png"
            image.save(os.path.join(save_dir, filename))
            
            # Display the image in Streamlit instead of using image.show()
            st.image(image, caption=f"Panel {panel_num}",use_container_width=True)
            return True
        else:
            st.error(f"Failed to fetch image {panel_num}. Status code: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error displaying image {panel_num}: {e}")
        return False

# Streamlit app setup
st.title("Dream Comic Generator")
st.write("Enter your dream description below and click the button to generate a comic. 在下方輸入您的夢境描述，然後點擊按鈕生成漫畫。")

# User input via Streamlit
prompt = st.text_area("Enter your dream text: 輸入您的夢境描述：", height=150)

# Generate comic when button is clicked
if st.button("Generate Comic"):
    if prompt:
        with st.spinner("Generating your dream comic... This may take a minute..."):
            data = {'dream_text': prompt}

            try:
                response = requests.post(f"{url}/api/generate-comic", data=data, timeout=600)

                # Parse and display the response
                response_data = response.json()
                
                st.subheader("DREAM COMIC GENERATION RESULTS")
                st.write(f"Session ID: {response_data['session_id']}")
                st.markdown("---")

                # Store session_id for image saving
                session_id = response_data['session_id']
                
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
