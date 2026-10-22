#!/usr/bin/env node
// Fixed Word layout. SPDX-License-Identifier: MIT.
// Input comes from receipts.py after all evidence checks pass.
"use strict";

const fs = require("node:fs");
const os = require("node:os");
const {
  AlignmentType, BorderStyle, Document, ExternalHyperlink, HeadingLevel,
  ImageRun, Packer, Paragraph, Table, TableCell, TableRow, TextRun, WidthType,
} = require("docx");
const { imageSize } = require("image-size");

const FONT = {
  ascii: "Arial", hAnsi: "Arial",
  eastAsia: os.platform() === "darwin" ? "PingFang SC"
    : os.platform() === "win32" ? "Microsoft YaHei" : "Noto Sans CJK SC",
};
const WIDTH = 9638; // A4, 20 mm margins.
const NO_BORDER = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const BORDERS = Object.fromEntries(
  ["top", "bottom", "left", "right", "insideHorizontal", "insideVertical"]
    .map((edge) => [edge, NO_BORDER]),
);

function runs(value, options = {}) {
  return String(value).split(/\r?\n/).map((line, index) =>
    new TextRun({ text: line, ...(index ? { break: 1 } : {}), ...options }));
}

function paragraph(value, options = {}) {
  return new Paragraph({
    spacing: { after: 90, line: 276 },
    children: runs(value),
    ...options,
  });
}

function field(label, value) {
  return new Paragraph({
    spacing: { after: 90, line: 276 },
    children: [new TextRun({ text: label + "：", bold: true }), ...runs(value)],
  });
}

function quotePair(original, translation) {
  const cell = (width, content) => new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders: BORDERS,
    margins: { top: 60, bottom: 60, left: 0, right: 100 },
    children: [paragraph(content)],
  });
  return new Table({
    width: { size: WIDTH, type: WidthType.DXA },
    columnWidths: [900, WIDTH - 900],
    borders: BORDERS,
    rows: [["原文", original], ["中文对照", translation]].map(([label, content]) =>
      new TableRow({ cantSplit: true, children: [
        cell(900, label), cell(WIDTH - 900, content),
      ] })),
  });
}

function imageBlock(item) {
  const data = Buffer.from(item.png_base64, "base64");
  const dimensions = imageSize(data);
  if (dimensions.type !== "png" || !dimensions.width || !dimensions.height) {
    throw new Error("Evidence image must be a PNG with known dimensions");
  }
  // Both limits preserve the original aspect ratio; no crop or recompression.
  const scale = Math.min(578 / dimensions.width, 540 / dimensions.height);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 80, after: 60 },
      children: [new ImageRun({
        type: "png", data,
        transformation: {
          width: Math.round(dimensions.width * scale),
          height: Math.round(dimensions.height * scale),
        },
        altText: { title: item.label, description: item.location, name: item.label },
      })],
    }),
    paragraph(item.label + "｜" + item.location, {
      alignment: AlignmentType.CENTER,
      children: runs(item.label + "｜" + item.location, { size: 18, color: "555555" }),
      spacing: { after: 140, line: 240 },
    }),
  ];
}

async function main() {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  if (input.layout !== "minimal-evidence-v1" || !Array.isArray(input.evidence)
      || input.evidence.length === 0) {
    throw new Error("Only the fixed minimal evidence layout is supported");
  }
  const children = [paragraph("论文原文、中文对照与红线截图", {
    heading: HeadingLevel.HEADING_1,
  })];
  input.evidence.forEach((item, index) => {
    children.push(
      paragraph(`证据 ${index + 1}：${item.claim}`, { heading: HeadingLevel.HEADING_2 }),
      field("出处", item.citation),
      field("来源资格与证据类别", item.eligibility),
      new Paragraph({
        spacing: { after: 90, line: 276 },
        children: [
          new TextRun({ text: "DOI / 原文链接：", bold: true }),
          new ExternalHyperlink({
            link: item.url,
            children: [new TextRun({ text: item.url, style: "Hyperlink" })],
          }),
        ],
      }),
      field("对应用户论文 / 目的", item.target_location),
      field("用户原句", item.target_quote),
      field("具体相关事项", item.relevance),
      quotePair(item.original, item.translation),
      field("支持", item.supports),
      field("边界", item.limits),
      field("原文位置与归属", item.location),
      field("原始来源溯源", item.lineage),
    );
    for (const image of item.images) children.push(...imageBlock(image));
    for (const hop of item.hops) {
      children.push(field("引用追踪", hop.identity), field("引用段", hop.passage),
        field("参考文献条目", hop.reference));
      for (const image of hop.images) children.push(...imageBlock(image));
    }
  });
  const document = new Document({
    creator: "ShowYourReceipts",
    title: "论文原文、中文对照与红线截图",
    description: "Fixed evidence report generated from checked source records.",
    styles: {
      default: {
        document: { run: { font: FONT, size: 22, color: "111111" } },
      },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
          quickFormat: true, run: { font: FONT, size: 32, bold: true, color: "111111" },
          paragraph: { outlineLevel: 0, keepNext: false, keepLines: false,
            spacing: { before: 0, after: 200 } } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal",
          quickFormat: true, run: { font: FONT, size: 26, bold: true, color: "111111" },
          paragraph: { outlineLevel: 1, keepNext: false, keepLines: false,
            spacing: { before: 220, after: 100 } } },
      ],
    },
    sections: [{
      properties: { page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 },
      } },
      children,
    }],
  });
  process.stdout.write(await Packer.toBuffer(document));
}

main().catch((error) => {
  process.stderr.write(String(error.message) + "\n");
  process.exitCode = 2;
});
