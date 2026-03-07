import time
import threading
from display import Display
from colorama import Fore

def test_ui():
    print("Starting UI Test...")
    ui = Display()
    
    # Register some dummy tasks
    ui.register_task("t1", "Research: Black Hole Metric", color=Fore.GREEN)
    ui.register_task("t2", "Research: Entropy Bounds", color=Fore.GREEN)
    
    time.sleep(1)
    
    print("Simulating Queue Growth...")
    for i in range(1, 11):
        ui.update_queue_size(i)
        time.sleep(0.5)
        
    print("Simulating Queue Shrinkage...")
    for i in range(10, -1, -1):
        ui.update_queue_size(i)
        time.sleep(0.5)
        
    ui.shutdown()
    print("UI Test Complete.")

if __name__ == "__main__":
    test_ui()
