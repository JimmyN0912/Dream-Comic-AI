# Dream Comic Generator

A tool that transforms dream descriptions into visual comic panels using AI. This project consists of a client application built with Streamlit and a server component using Flask.

## Features

- Convert text descriptions of dreams into four-panel comics
- Generate images based on dream descriptions using Stable Diffusion
- Translation of panel descriptions into Traditional Chinese
- User-friendly web interface
- API endpoints for programmatic access

## Prerequisites

### For Server
- Python 3.7+
- Flask
- Groq API key
- Local text generation API (running on port 5001)
- Stable Diffusion API (running on port 7861)
- PIL (Pillow)
- python-dotenv

### For Client
- Python 3.7+
- Streamlit
- Requests
- PIL (Pillow)
