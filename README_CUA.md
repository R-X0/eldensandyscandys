# OpenAI Computer Using Agent (CUA) - Basic Implementation

This is a basic implementation of OpenAI's Computer Using Agent (CUA) that can interact with web browsers and perform automated tasks.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

### Basic Example
```python
from cua_agent import ComputerUsingAgent, CUAConfig
import os

config = CUAConfig(openai_api_key=os.getenv("OPENAI_API_KEY"))
agent = ComputerUsingAgent(config)

result = agent.run_task("Search for 'OpenAI' on Google")
print(result)
```

### Run the example script:
```bash
python cua_agent.py
```

## Features

- Screenshot capture and visual analysis
- Browser automation with Playwright
- OpenAI API integration for computer use
- Configurable viewport and step limits
- Error handling and cleanup

## Current Limitations

- Action parsing is not fully implemented
- Limited to basic browser interactions
- No persistent conversation memory
- Simplified error handling

## Next Steps

- Implement proper JSON action parsing
- Add more sophisticated action types
- Improve error recovery
- Add conversation context management