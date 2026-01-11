# citybike-rebalancing-agent
Check out our live demo here:
**[Demo Webpage](https://huggingface.co)**


## Overview
In this project we have created an agent which plans how citybikes should be moved by a truckdriver in Palma. We imagine that the truckdriver works for a citybikes company in Palma and can move a certain amount of bikes in his truck. The goal of our planning agent is to work in the same way as a human planner would, by getting info about how long the truckdriver works and where he is starting, the planning agent is able to generate a route for the truckdriver and instructions on how many bikes to pickup and dropoff at every station. The route should make as many stations as possible optimally stacked with bikes, i.e lots of bikes in stations where bikes often are picked up, and less bikes (but not empty) in stations where lots of bikes are left. Since we are using an agent we also allow for special requests in the same way a human planning agent would, for example if the driver knows some part of the city is closed due to an event, we want our planning agent to account for this, and/or other special cases.

**Bike station overview in Palma**

![station overview](assets/overview.png)

A green dot means the station is full or almost full, a yellow dot means there is only a few bikes remaining, and a red dot means that the bike station is empty.

**Agentic workflow and pipeline overview**
We use the following structure of the agent and feature pipeline.
![pipeline image](assets/API.png)


## LLM and In-context Learning
We use he OpenAIs "gpt-4o-mini" and the LLM use in-context learning.


## Setup (to run locally)

1. Create a conda virtual environment:
```
conda create --name cr-agent python=3.10.14
conda activate cr-agent
```
2. Install project dependencies:
```
pip install -r requirements.txt
```
3. Insert Hopsworks and OpenAI API keys into .env (check .env.example for correct format) 
4. Host the website locally by
```
python app.py
```

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

