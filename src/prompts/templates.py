# Simple f-string templates for MVP
# In future, we can upgrade to Jinja2 if logic gets complex

INIT_FRAME_TEMPLATE = (
    "{subject}, {action}, {context}. "
    "{style_modifiers}, {lighting}, {camera}. "
    "High quality, 8k, detailed."
)

CLIP_PROMPT_TEMPLATE = (
    "{shot_archetype_desc} of {subject} {action}. "
    "{context}. "
    "{style_modifiers}. "
    "Fluid motion, cinematic lighting."
)
