#!/usr/bin/env python3
"""
Test script to check Docker connectivity and image availability
"""

import docker
from rich.console import Console

console = Console()

def test_docker():
    """Test Docker connectivity and image availability"""
    try:
        # Test Docker connection
        console.print("[cyan]Testing Docker connection...")
        client = docker.from_env()
        client.ping()
        console.print("[green]✓ Docker connection successful")
        
        # Check if base image exists
        base_image = "frdel/agent-zero-run:latest"
        console.print(f"[cyan]Checking for image: {base_image}")
        
        try:
            image = client.images.get(base_image)
            console.print(f"[green]✓ Image {base_image} found locally")
            console.print(f"[cyan]Image ID: {image.id}")
            console.print(f"[cyan]Image tags: {image.tags}")
        except docker.errors.ImageNotFound:
            console.print(f"[yellow]⚠ Image {base_image} not found locally")
            console.print(f"[cyan]Attempting to pull image...")
            try:
                client.images.pull(base_image)
                console.print(f"[green]✓ Successfully pulled {base_image}")
            except Exception as pull_error:
                console.print(f"[red]✗ Failed to pull image: {pull_error}")
                return False
        
        # Test container creation
        console.print("[cyan]Testing container creation...")
        try:
            container = client.containers.run(
                image=base_image,
                command="echo 'Hello from container'",
                remove=True,
                detach=False
            )
            console.print(f"[green]✓ Container test successful")
            console.print(f"[cyan]Output: {container.decode().strip()}")
        except Exception as container_error:
            console.print(f"[red]✗ Container test failed: {container_error}")
            return False
        
        console.print("[green]🎉 All Docker tests passed!")
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Docker test failed: {e}")
        return False

if __name__ == "__main__":
    test_docker() 