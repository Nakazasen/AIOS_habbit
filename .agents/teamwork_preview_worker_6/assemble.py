import json
import sys
from pathlib import Path

def main():
    root = Path("d:/Sandbox/AIOS_habbit")
    baseline_path = root / ".understand-anything" / "knowledge-graph.json"
    layers_tour_path = root / ".agents" / "teamwork_preview_worker_1" / "layers_tour_translated.json"
    chunk1_path = root / ".agents" / "teamwork_preview_worker_2" / "nodes_chunk_1.json"
    chunk2_path = root / ".agents" / "teamwork_preview_worker_3" / "nodes_chunk_2.json"
    chunk3_path = root / ".agents" / "teamwork_preview_worker_4" / "nodes_chunk_3.json"
    chunk4_path = root / ".agents" / "teamwork_preview_worker_5" / "nodes_chunk_4.json"

    print("Reading baseline...")
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)

    version = baseline_data["version"]
    edges = baseline_data["edges"]

    print(f"Baseline version: {version}")
    print(f"Baseline edges count: {len(edges)}")
    print(f"Baseline nodes count: {len(baseline_data['nodes'])}")

    print("Reading layers and tour...")
    with open(layers_tour_path, "r", encoding="utf-8") as f:
        layers_tour_data = json.load(f)

    project = layers_tour_data["project"]
    layers = layers_tour_data["layers"]
    tour = layers_tour_data["tour"]
    print(f"Layers count: {len(layers)}, Tour steps count: {len(tour)}")

    print("Reading node chunks...")
    with open(chunk1_path, "r", encoding="utf-8") as f:
        chunk1 = json.load(f)
    with open(chunk2_path, "r", encoding="utf-8") as f:
        chunk2 = json.load(f)
    with open(chunk3_path, "r", encoding="utf-8") as f:
        chunk3 = json.load(f)
    with open(chunk4_path, "r", encoding="utf-8") as f:
        chunk4 = json.load(f)

    print(f"Chunk 1 length: {len(chunk1)}")
    print(f"Chunk 2 length: {len(chunk2)}")
    print(f"Chunk 3 length: {len(chunk3)}")
    print(f"Chunk 4 length: {len(chunk4)}")

    all_nodes = chunk1 + chunk2 + chunk3 + chunk4
    print(f"Total concatenated nodes: {len(all_nodes)}")

    # Verify ID match with baseline nodes
    baseline_ids = [n["id"] for n in baseline_data["nodes"]]
    assembled_ids = [n["id"] for n in all_nodes]

    if baseline_ids == assembled_ids:
        print("✓ Assembled node IDs match baseline node IDs in exact sequence!")
    else:
        print("❌ Node ID sequence mismatch!")
        missing = set(baseline_ids) - set(assembled_ids)
        extra = set(assembled_ids) - set(baseline_ids)
        print(f"Missing: {missing}")
        print(f"Extra: {extra}")
        for idx, (b_id, a_id) in enumerate(zip(baseline_ids, assembled_ids)):
            if b_id != a_id:
                print(f"Mismatch at index {idx}: baseline='{b_id}' vs assembled='{a_id}'")
                break
        sys.exit(1)

    # Build final dictionary
    assembled_graph = {
        "version": version,
        "project": project,
        "nodes": all_nodes,
        "edges": edges,
        "layers": layers,
        "tour": tour
    }

    # Backup original before overwriting (in worker_6 directory for audit if needed)
    backup_path = root / ".agents" / "teamwork_preview_worker_6" / "knowledge-graph.json.bak"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f, indent=2, ensure_ascii=False)
    print(f"Created backup at {backup_path}")

    # Overwrite destination
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(assembled_graph, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Successfully wrote assembled graph to {baseline_path}")

if __name__ == "__main__":
    main()
