import base64
import anthropic
import sys
from dotenv import load_dotenv

from schemas.parties import Parties
from schemas.terms import Term


load_dotenv()


def load_pdf(path: str) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def iter_uncited_paths(data, cited_text: str, path: str = ""):
    if isinstance(data, dict):
        for key, value in data.items():
            yield from iter_uncited_paths(
                value, cited_text, f"{path}.{key}" if path else key
            )
    elif isinstance(data, list):
        for i, item in enumerate(data):
            yield from iter_uncited_paths(item, cited_text, f"{path}[{i}]")
    elif isinstance(data, str):
        parts = [p.strip() for p in data.split(",")]
        if data not in cited_text and not all(p in cited_text for p in parts):
            yield path, data


tools = [
    {
        "name": "extract_parties",
        "description": "Extract the contracting parties from the agreement.",
        "input_schema": Parties.model_json_schema(),
    },
    {
        "name": "extract_terms",
        "description": "Extract the term details from the agreement.",
        "input_schema": Term.model_json_schema(),
    },
]

TOOL_MODELS = {
    "extract_parties": Parties,
    "extract_terms": Term,
}


def main():
    contract_file_path = " ".join(sys.argv[1:])
    pdf_base64 = load_pdf(contract_file_path)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        tools=tools,
        tool_choice={"type": "auto"},
        system="You MUST quote the relevant document passages before calling any extraction tool. Always provide cited text first, then the tool call.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64,
                        },
                        "citations": {"enabled": True},
                    },
                    {
                        "type": "text",
                        "text": "Extract all contract terms from this document. For each section you extract, first quote the relevant passages from the document, then call the appropriate extraction tool with the structured data. Use only the tools provided.",
                    },
                ],
            }
        ],
    )

    # Parse response
    citations = []
    tool_calls = []

    for block in response.content:
        if block.type == "text" and block.citations:
            citations.extend(block.citations)
        elif block.type == "tool_use":
            tool_calls.append(block)

    # Pydantic validation
    validated_results = {}
    for tool_call in tool_calls:
        try:
            validated = TOOL_MODELS[tool_call.name](**tool_call.input)
            validated_results[tool_call.name] = validated
        except Exception as e:
            print(f"{tool_call.name}: {e}")

    # Citation grounding check — using validated model output so only strings are checked
    cited_texts = [c.cited_text for c in citations]
    full_cited = "\n\n".join(cited_texts)

    warning_count = 0
    for name, validated in validated_results.items():
        for path, value in iter_uncited_paths(validated.model_dump(), full_cited):
            warning_count += 1
            print(f"{name} — {path}: '{value}'")

    if warning_count == 0:
        print("All values grounded in citations")
    else:
        print(f"\n{warning_count} value(s) not found in cited text")

    print(validated_results)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <contract_file_path>")
        sys.exit(1)
    main()
