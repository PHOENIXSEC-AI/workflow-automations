import click


class Crayons:
    @staticmethod
    def color_agent_name(agent_name: str) -> str:
        """Return a colored agent name."""
        return click.style(agent_name, fg="blue", bold=False)
    
    def color_duration(duration: float) -> str:
        """Return a colored duration string."""
        return click.style(f"{duration:.2f}s", fg="blue")
    
    def color_flow_name(flow_name:str) -> str:
        return click.style(f"{flow_name}", fg="magenta")
    
    def color_str(value:str) -> str:
        return click.style(f"{value}", fg="blue")