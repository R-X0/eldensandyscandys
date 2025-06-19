#!/usr/bin/env python3
"""
Basic OpenAI Computer Using Agent (CUA) implementation
"""

import os
import base64
from io import BytesIO
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from openai import OpenAI
from playwright.sync_api import sync_playwright, Page, Browser
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

@dataclass
class CUAConfig:
    openai_api_key: str
    model: str = "gpt-4o"
    max_steps: int = 10
    viewport_width: int = 1280
    viewport_height: int = 720

class ComputerUsingAgent:
    def __init__(self, config: CUAConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    def start_browser(self):
        """Initialize browser and page"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.page = self.browser.new_page()
        self.page.set_viewport_size(
            width=self.config.viewport_width, 
            height=self.config.viewport_height
        )
        
    def stop_browser(self):
        """Clean up browser resources"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            
    def take_screenshot(self) -> str:
        """Take screenshot and return as base64 string"""
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        screenshot = self.page.screenshot()
        return base64.b64encode(screenshot).decode()
        
    def execute_action(self, action: Dict[str, Any]) -> bool:
        """Execute a computer action"""
        if not self.page:
            return False
            
        try:
            action_type = action.get("type")
            
            if action_type == "click":
                x, y = action["x"], action["y"]
                self.page.mouse.click(x, y)
                
            elif action_type == "type":
                text = action["text"]
                self.page.keyboard.type(text)
                
            elif action_type == "scroll":
                delta_y = action.get("delta_y", 100)
                self.page.mouse.wheel(0, delta_y)
                
            elif action_type == "key":
                key = action["key"]
                self.page.keyboard.press(key)
                
            elif action_type == "goto":
                url = action["url"]
                self.page.goto(url)
                
            else:
                print(f"Unknown action type: {action_type}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error executing action: {e}")
            return False
            
    def call_cua_api(self, screenshot: str, instruction: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Call OpenAI API with screenshot and instruction"""
        
        messages = conversation_history + [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"I need help with this task: {instruction}\n\nPlease analyze the screenshot and provide the next action to take. Respond with a JSON object containing the action details."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot}"
                    }
                }
            ]
        }]
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.1
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "usage": response.usage
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    def run_task(self, instruction: str, start_url: str = "https://www.google.com") -> Dict[str, Any]:
        """Run a complete CUA task"""
        
        self.start_browser()
        conversation_history = []
        
        try:
            # Navigate to starting URL
            self.page.goto(start_url)
            
            for step in range(self.config.max_steps):
                print(f"Step {step + 1}: Taking screenshot...")
                screenshot = self.take_screenshot()
                
                print(f"Step {step + 1}: Calling CUA API...")
                result = self.call_cua_api(screenshot, instruction, conversation_history)
                
                if not result["success"]:
                    return {
                        "success": False,
                        "error": f"API call failed: {result['error']}",
                        "step": step + 1
                    }
                
                response_text = result["response"]
                print(f"Step {step + 1}: Response: {response_text}")
                
                # Add to conversation history
                conversation_history.append({
                    "role": "assistant",
                    "content": response_text
                })
                
                # Check if task is complete
                if "task_complete" in response_text.lower() or "done" in response_text.lower():
                    return {
                        "success": True,
                        "message": "Task completed successfully",
                        "steps": step + 1
                    }
                
                # TODO: Parse action from response and execute
                # This is a simplified version - in practice you'd need to parse JSON
                print(f"Step {step + 1}: Action parsing not implemented yet")
                break
                
            return {
                "success": False,
                "message": "Max steps reached without completion",
                "steps": self.config.max_steps
            }
            
        finally:
            self.stop_browser()

def main():
    """Example usage"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return
        
    config = CUAConfig(openai_api_key=api_key)
    agent = ComputerUsingAgent(config)
    
    # Example task
    instruction = "Search for 'OpenAI' on Google"
    result = agent.run_task(instruction)
    
    print(f"Task result: {result}")

if __name__ == "__main__":
    main()