# citybike-rebalancing-agent

**[Demo Webpage](https://huggingface.co)**


## Overview
![pipeline image](assets/pipeline.png)


## Setup

1. Create a conda virtual environment:
```
conda create --name cr-agent python=3.10.14
conda activate cr-agent
```
2. Install project dependencies:
```
pip install -r requirements.txt
```
3. Hopsworks .env
4.

## Files
- **[placeholder.py](placeholder.py)**: Placeholder text


## Testing

Run individual tests with full output:
```bash
python -m tests.test_llm_hf
python -m tests.test_orchestrator
```

Run all tests using pytest:
```bash
pytest tests/
```

Run tests with verbose output:
```bash
pytest tests/ -v
```

Run a specific test file with pytest:
```bash
pytest tests/test_llm_hf.py -v
```

