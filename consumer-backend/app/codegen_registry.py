STACK_REGISTRY = {
    "frontend": {
        "vue": {"label": "Vue", "language": "TypeScript"},
        "react": {"label": "React", "language": "TypeScript"},
    },
    "backend": {
        "fastapi": {"label": "Python FastAPI", "language": "Python"},
        "nestjs": {"label": "Node.js NestJS", "language": "TypeScript"},
        "springboot": {"label": "Java Spring Boot", "language": "Java"},
    },
    "database": {
        "mysql": {"label": "MySQL", "language": "SQL"},
        "postgresql": {"label": "PostgreSQL", "language": "SQL"},
    },
    "deploy": {
        "ubuntu-nginx": {"label": "Ubuntu + Nginx", "language": "Nginx"},
        "docker": {"label": "Docker", "language": "Dockerfile"},
    },
}


def validate_stack_choice(layer: str, value: str) -> str:
    if value not in STACK_REGISTRY[layer]:
        allowed = ", ".join(STACK_REGISTRY[layer].keys())
        raise ValueError(f"Unsupported {layer} stack '{value}'. Allowed: {allowed}")
    return value


def get_stack_labels(stack: dict) -> dict:
    return {layer: STACK_REGISTRY[layer][key]["label"] for layer, key in stack.items()}


def stack_registry_out() -> dict:
    return {
        layer: [
            {"key": key, "label": value["label"], "language": value["language"]}
            for key, value in options.items()
        ]
        for layer, options in STACK_REGISTRY.items()
    }
