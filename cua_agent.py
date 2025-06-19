#!/usr/bin/env python3
"""
Basic OpenAI Computer Using Agent (CUA) implementation
"""

import os
import base64
import json
import re
import time
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
        self.page.set_viewport_size({
            'width': self.config.viewport_width, 
            'height': self.config.viewport_height
        })
        
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
        
    def parse_and_execute_action(self, response_text: str) -> bool:
        """Parse action from response and execute it"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                action_data = json.loads(json_str)
            else:
                # Try to find JSON directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    action_data = json.loads(json_match.group())
                else:
                    print("No valid JSON found in response")
                    return False
            
            action = action_data.get("action")
            details = action_data.get("details", {})
            
            if action == "click":
                # Look for coordinates or try to find element
                if "x" in details and "y" in details:
                    self.page.mouse.click(details["x"], details["y"])
                elif "selector" in details:
                    self.page.click(details["selector"])
                else:
                    print("Click action missing coordinates or selector")
                    return False
                    
            elif action == "type" or action == "type_search_query":
                # Type text, either directly or in a specific field
                text = details.get("query") or details.get("text", "")
                if "selector" in details:
                    self.page.fill(details["selector"], text)
                else:
                    # Try to find search input
                    try:
                        self.page.fill('input[name="q"]', text)  # Google search
                    except:
                        try:
                            self.page.fill('input[type="search"]', text)
                        except:
                            self.page.keyboard.type(text)
                            
            elif action == "press_enter" or action == "submit":
                self.page.keyboard.press("Enter")
                
            elif action == "click_search" or action == "search":
                # Try to click search button
                try:
                    self.page.click('input[value="Google Search"]')
                except:
                    try:
                        self.page.click('button[type="submit"]')
                    except:
                        self.page.keyboard.press("Enter")
                        
            elif action == "scroll":
                delta_y = details.get("delta_y", 300)
                self.page.mouse.wheel(0, delta_y)
                
            elif action == "wait":
                time.sleep(details.get("seconds", 1))
                
            else:
                print(f"Unknown action: {action}")
                return False
                
            return True
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return False
        except Exception as e:
            print(f"Error executing action: {e}")
            return False
            
    def call_cua_api(self, screenshot: str, instruction: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Call OpenAI API with screenshot and instruction"""
        
        system_prompt = """You are a computer-using agent. Analyze the screenshot and provide the next action to take.

Available actions:
- type_search_query: Type text in search field. Format: {"action": "type_search_query", "details": {"query": "text to type"}}
- click: Click at coordinates or selector. Format: {"action": "click", "details": {"x": 100, "y": 200}} or {"action": "click", "details": {"selector": "button"}}
- press_enter: Press Enter key. Format: {"action": "press_enter", "details": {}}
- click_search: Click search button. Format: {"action": "click_search", "details": {}}
- scroll: Scroll page. Format: {"action": "scroll", "details": {"delta_y": 300}}
- wait: Wait for seconds. Format: {"action": "wait", "details": {"seconds": 2}}

Always respond with valid JSON in the format above. If the task appears complete, include "task_complete": true in your response."""
        
        messages = [{
            "role": "system",
            "content": system_prompt
        }] + conversation_history + [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Task: {instruction}\n\nAnalyze this screenshot and provide the next action as JSON:"
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
                
                # Parse and execute action
                action_success = self.parse_and_execute_action(response_text)
                if action_success:
                    print(f"Step {step + 1}: Action executed successfully")
                    # Wait a bit for page to load
                    time.sleep(2)
                else:
                    print(f"Step {step + 1}: Action execution failed")
                
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