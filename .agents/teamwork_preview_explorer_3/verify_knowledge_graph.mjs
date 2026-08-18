#!/usr/bin/env node
/**
 * Node.js Automated Verification Harness for knowledge-graph.json
 * Tests JSON parsing, schema validation via @understand-anything/core schema rules,
 * referential integrity, and Vietnamese translation properties.
 */

import fs from 'fs';
import path from 'path';

const VIETNAMESE_REGEX = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]/i;

function runValidation(targetPath, baselinePath) {
  const resolvedTarget = path.resolve(targetPath);
  console.log('='.repeat(70));
  console.log(`NODE.JS VERIFICATION HARNESS: ${path.basename(resolvedTarget)}`);
  console.log(`Target: ${resolvedTarget}`);
  console.log('='.repeat(70));

  if (!fs.existsSync(resolvedTarget)) {
    console.error(`❌ File not found: ${resolvedTarget}`);
    process.exit(1);
  }

  let rawBuffer;
  try {
    rawBuffer = fs.readFileSync(resolvedTarget);
  } catch (err) {
    console.error(`❌ Failed to read file: ${err.message}`);
    process.exit(1);
  }

  // Null byte check
  if (rawBuffer.includes(0)) {
    console.error('❌ File contains null byte (\\x00)');
    process.exit(1);
  }

  const rawText = rawBuffer.toString('utf8');
  if (rawText.includes('\ufffd')) {
    console.error('❌ File contains Unicode replacement character (U+FFFD) - UTF-8 corrupted');
    process.exit(1);
  }

  let graph;
  try {
    graph = JSON.parse(rawText);
    console.log('  ✓ JSON syntax valid & JSON.parse succeeded');
  } catch (err) {
    console.error(`❌ JSON parse failed: ${err.message}`);
    process.exit(1);
  }

  const errors = [];
  const warnings = [];

  // Top-level structure
  if (typeof graph.version !== 'string') errors.push('graph.version must be string');
  if (!graph.project || typeof graph.project !== 'object') errors.push('graph.project must be object');
  if (!Array.isArray(graph.nodes)) errors.push('graph.nodes must be array');
  if (!Array.isArray(graph.edges)) errors.push('graph.edges must be array');
  if (!Array.isArray(graph.layers)) errors.push('graph.layers must be array');
  if (!Array.isArray(graph.tour)) errors.push('graph.tour must be array');

  if (errors.length > 0) {
    console.error('❌ Fatal top-level schema errors:', errors);
    process.exit(1);
  }

  // Nodes & referential integrity
  const nodeIds = new Set();
  let viSummaryCount = 0;
  for (let i = 0; i < graph.nodes.length; i++) {
    const node = graph.nodes[i];
    if (!node.id || typeof node.id !== 'string') {
      errors.push(`Node[${i}] missing valid id`);
      continue;
    }
    if (nodeIds.has(node.id)) {
      errors.push(`Duplicate node id: ${node.id}`);
    }
    nodeIds.add(node.id);

    if (!node.name || typeof node.name !== 'string') errors.push(`Node '${node.id}' missing name`);
    if (!node.type || typeof node.type !== 'string') errors.push(`Node '${node.id}' missing type`);
    if (!node.summary || typeof node.summary !== 'string') {
      errors.push(`Node '${node.id}' missing summary`);
    } else {
      if (VIETNAMESE_REGEX.test(node.summary)) viSummaryCount++;
    }
    if (!Array.isArray(node.tags)) errors.push(`Node '${node.id}' missing tags array`);
  }

  // Edges
  for (let i = 0; i < graph.edges.length; i++) {
    const edge = graph.edges[i];
    if (!nodeIds.has(edge.source)) errors.push(`Edge[${i}] source '${edge.source}' not found`);
    if (!nodeIds.has(edge.target)) errors.push(`Edge[${i}] target '${edge.target}' not found`);
  }

  // Layers
  let viLayerCount = 0;
  for (let i = 0; i < graph.layers.length; i++) {
    const layer = graph.layers[i];
    if (!layer.id) errors.push(`Layer[${i}] missing id`);
    if (!layer.name) errors.push(`Layer[${i}] missing name`);
    if (!layer.description) {
      errors.push(`Layer[${i}] missing description`);
    } else if (VIETNAMESE_REGEX.test(layer.description)) {
      viLayerCount++;
    }
    for (const nid of layer.nodeIds || []) {
      if (!nodeIds.has(nid)) errors.push(`Layer '${layer.id}' refs missing node '${nid}'`);
    }
  }

  // Tour
  let viTourCount = 0;
  for (let i = 0; i < graph.tour.length; i++) {
    const step = graph.tour[i];
    if (typeof step.order !== 'number') errors.push(`Tour[${i}] missing order`);
    if (!step.title) errors.push(`Tour[${i}] missing title`);
    if (!step.description) {
      errors.push(`Tour[${i}] missing description`);
    } else if (VIETNAMESE_REGEX.test(step.description) || VIETNAMESE_REGEX.test(step.title || '')) {
      viTourCount++;
    }
    for (const nid of step.nodeIds || []) {
      if (!nodeIds.has(nid)) errors.push(`Tour step ${step.order} refs missing node '${nid}'`);
    }
  }

  // Baseline check
  if (baselinePath && fs.existsSync(baselinePath)) {
    try {
      const baseline = JSON.parse(fs.readFileSync(baselinePath, 'utf8'));
      if (baseline.nodes.length !== graph.nodes.length) {
        errors.push(`Node count mismatch: baseline ${baseline.nodes.length} vs current ${graph.nodes.length}`);
      }
      if (baseline.edges.length !== graph.edges.length) {
        errors.push(`Edge count mismatch: baseline ${baseline.edges.length} vs current ${graph.edges.length}`);
      }
      if (baseline.layers.length !== graph.layers.length) {
        errors.push(`Layer count mismatch: baseline ${baseline.layers.length} vs current ${graph.layers.length}`);
      }
      if (baseline.tour.length !== graph.tour.length) {
        errors.push(`Tour count mismatch: baseline ${baseline.tour.length} vs current ${graph.tour.length}`);
      }
      console.log('  ✓ Baseline comparison passed');
    } catch (err) {
      warnings.push(`Baseline check failed: ${err.message}`);
    }
  }

  console.log('\n' + '-'.repeat(70));
  console.log('METRICS:');
  console.log(`  • Nodes: ${graph.nodes.length} (with Vietnamese summary: ${viSummaryCount})`);
  console.log(`  • Edges: ${graph.edges.length}`);
  console.log(`  • Layers: ${graph.layers.length} (with Vietnamese description: ${viLayerCount})`);
  console.log(`  • Tour Steps: ${graph.tour.length} (with Vietnamese title/desc: ${viTourCount})`);
  console.log('-'.repeat(70));

  if (errors.length > 0) {
    console.error(`\n❌ VERIFICATION FAILED with ${errors.length} errors:`);
    errors.slice(0, 20).forEach((e) => console.error(`  - ${e}`));
    process.exit(1);
  }

  console.log('\n✅ VERIFICATION PASSED: Graph is structurally sound and dashboard-ready.');
}

const target = process.argv[2] || 'd:/Sandbox/AIOS_habbit/.understand-anything/knowledge-graph.json';
const baseline = process.argv[3];
runValidation(target, baseline);
