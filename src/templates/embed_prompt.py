emb_prompt = """
Generate a concise description of the following document chunk in 1-2 lines. 
Do NOT include any instructional text like 'Here is a description' or formatting like <br>. 
Only provide the description itself, tailored to the chunk's content. 

Examples:\n

- Input: '## Section 1\nSome text here'\n  
- Output: 'Brief overview of a project section.'\n

- Input: '| Time | Person |\n|-----|--------|\n| 10:00| Alice  |'\n  
- Output: 'Table listing a scheduled time and assigned person.'\n\n

Chunk content:\n
{page_content}

"""