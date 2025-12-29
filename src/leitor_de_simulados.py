import argparse

# Must be imported before any other module
from utils.log import LoggingSystem
from utils.memory import MemoryTracker
from gui.app import WindowApplication


def main(log_level: str, memory_tracking: bool, memory_verbose: bool):
    LoggingSystem.initialize(log_level=log_level)
    
    # Initialize memory tracking if requested
    if memory_tracking:
        MemoryTracker.enable(print_on_track=memory_verbose)
    
    app = WindowApplication()
    
    # Print memory report on exit if tracking was enabled
    if memory_tracking:
        import atexit
        atexit.register(lambda: MemoryTracker.print_report(detailed=True))
    
    app.mainloop()
    LoggingSystem.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Leitor de Simulados")
        
    parser.add_argument(
        "--loglevel",
        choices=["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--track-memory",
        action="store_true",
        help="Enable memory tracking for debugging"
    )
    parser.add_argument(
        "--memory-verbose",
        action="store_true",
        help="Print each memory allocation/deallocation event (requires --track-memory)"
    )
    args = parser.parse_args()
    main(
        log_level=args.loglevel, 
        memory_tracking=args.track_memory,
        memory_verbose=args.memory_verbose
    )