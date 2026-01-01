# Use HF Spaces base image
FROM ghcr.io/huggingface/spaces-pytorch-gpu:latest

WORKDIR /app

# Copy project
COPY . .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Launch Gradio
CMD ["python", "app.py"]
