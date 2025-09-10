import requests

def fetch_json(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def generate_offsets_py(offsets, client):
    if not offsets or not client:
        return None

    lines = [
        "class Offsets:",
        "    try:",
        "        from requests import get",
        "        offset = get(\"https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json\").json()",
        "        client = get(\"https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json\").json()",
        ""
    ]

    # Dump all offsets from offsets.json
    for module_name, module_offsets in offsets.items():
        for key in module_offsets:
            lines.append(f"        {key} = offset['{module_name}']['{key}']")

    lines.append("")

    # Dump all fields from client.json
    for module_name, module_data in client.items():
        classes = module_data.get("classes", {})
        for class_name, class_data in classes.items():
            fields = class_data.get("fields", {})
            for field_name, field_value in fields.items():
                # Special case for m_pBoneArray
                if field_name == "m_modelState" and class_name == "CSkeletonInstance":
                    lines.append(f"        m_pBoneArray = client['{module_name}']['classes']['{class_name}']['fields']['{field_name}'] + 128")
                lines.append(f"        {field_name} = client['{module_name}']['classes']['{class_name}']['fields']['{field_name}']")

    lines.append("    except:")
    lines.append("        exit(\"Error: Invalid offsets, wait for an update\")")

    return "\n".join(lines)

def main():
    print("Fetching offset data...")
    offsets = fetch_json("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json")
    client = fetch_json("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json")

    print("Generating offsets.py...")
    result = generate_offsets_py(offsets, client)

    if result:
        with open("offsets.py", "w", encoding="utf-8") as f:
            f.write(result)
        print("offsets.py has been created with all offsets and m_pBoneArray included.")
    else:
        print("Failed to generate offsets.py due to missing data.")

if __name__ == "__main__":
    main()
