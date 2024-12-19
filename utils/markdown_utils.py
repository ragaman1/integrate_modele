# utils/markdown_utils.py

import re

def is_markdown_complete(text: str) -> bool:
    """
    Checks if all Markdown code blocks and bold markers are properly closed.

    Args:
        text (str): The text to check.

    Returns:
        bool: True if all Markdown entities are closed, False otherwise.
    """
    # Count occurrences of ```
    code_block_count = len(re.findall(r'```', text))
    # Count occurrences of `
    code_count = len(re.findall(r'`', text))
    # Count occurrences of **
    bold_count = len(re.findall(r'\*\*', text))

    # Check if code blocks are properly closed
    if code_block_count % 2 != 0:
        return False
    # Check if codes are properly closed
    if code_count % 2 != 0:
        return False

    # Check if bold markers are properly closed
    if bold_count % 2 != 0:
        return False

    return True

import re

def escape_markdown_v2(text):
    """
    Escape Markdown V2 special characters outside of code blocks and links,
    and apply Markdown V2 formatting, including inline code formatting.

    Args:
        text (str): The input text containing Markdown.

    Returns:
        str: The text with Markdown V2 characters escaped appropriately.
    """
    # Define Markdown V2 special characters that need to be escaped
    escape_chars = r'_[]()~>#+\-=\|{}.!\\'

    # Regular expression to match Markdown links: [text](url)
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    # Function to escape special characters in a given text
    def escape_special_chars(s):
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', s)

    # Function to apply Markdown V2 formatting to non-link, non-code parts
    def apply_markdown_formatting(part):
        # Convert headers (lines starting with '#') to bold text
        part = re.sub(r'^(#+)\s*(.*)', lambda m: f"*{m.group(2).strip()}*", part, flags=re.MULTILINE)
        # Bold text (assuming **text** should be converted to *text*)
        part = re.sub(r'\*\*(.*?)\*\*', r'*\1*', part)
        # Escape special characters
        part = escape_special_chars(part)
        return part

    # Function to convert asterisks to hyphens for bullet lists
    def convert_bullets(text):
        # Replace lines starting with '*' followed by a space with '- '
        return re.sub(r'^\* ', '- ', text, flags=re.MULTILINE)

    # Split the text into parts, separating code blocks
    parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)

    # Process each part separately
    processed_parts = []
    for part in parts:
        if part.startswith('```') and part.endswith('```'):
            # It's a code block; leave it unescaped
            processed_parts.append(part)
        else:
            # Within this part, further split to handle links
            segments = link_pattern.split(part)
            # The split will result in: [text_before_link, link_text, link_url, text_after_link, ...]
            # We will process the text before and after links, but leave links intact

            # Initialize an empty string to accumulate the processed text
            processed_text = ""

            # Iterate over the segments
            for i in range(0, len(segments), 3):
                # Process the non-link text
                non_link_text = segments[i]
                if non_link_text:
                    # Convert bullet list asterisks to hyphens
                    non_link_text = convert_bullets(non_link_text)
                    processed_text += apply_markdown_formatting(non_link_text)
                
                # Check if there's a link in this segment
                if i + 1 < len(segments):
                    link_text = segments[i + 1]
                    link_url = segments[i + 2]
                    # Escape special characters in link text and URL if necessary
                    escaped_link_text = escape_special_chars(link_text)
                    escaped_link_url = escape_special_chars(link_url)
                    # Reconstruct the link without escaping the brackets and parentheses
                    processed_text += f'[{escaped_link_text}]({escaped_link_url})'

            # Append the processed text for this part
            processed_parts.append(processed_text)

    # Reassemble the message with code blocks unescaped
    return ''.join(processed_parts)