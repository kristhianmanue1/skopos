// Extracción local interna; el host valida política, rutas y límites antes de invocar.
import Foundation
import PDFKit
import Vision

func region(_ rectangle: CGRect, in page: CGRect) -> [Double] {
    let x0 = (rectangle.minX - page.minX) / page.width
    let x1 = (rectangle.maxX - page.minX) / page.width
    let y0 = 1.0 - (rectangle.maxY - page.minY) / page.height
    let y1 = 1.0 - (rectangle.minY - page.minY) / page.height
    return [x0, y0, x1, y1].map { min(1.0, max(0.0, Double($0))) }
}

func ocrRegion(_ rectangle: CGRect) -> [Double] {
    return [Double(rectangle.minX), Double(1.0 - rectangle.maxY),
            Double(rectangle.maxX), Double(1.0 - rectangle.minY)]
}

func extractNative(_ page: PDFPage) -> [[String: Any]] {
    let content = page.string ?? ""
    guard !content.isEmpty else { return [] }
    let range = NSRange(location: 0, length: (content as NSString).length)
    let bounds = page.bounds(for: .cropBox)
    let lines = page.selection(for: range)?.selectionsByLine() ?? []
    return lines.compactMap { line in
        guard let text = line.string?.trimmingCharacters(in: .whitespacesAndNewlines),
              !text.isEmpty else { return nil }
        return ["text": text, "bbox": region(line.bounds(for: page), in: bounds)]
    }
}

func extractOcr(_ path: String) -> [String: Any] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["es-ES"]
    do {
        try VNImageRequestHandler(url: URL(fileURLWithPath: path)).perform([request])
        let lines: [[String: Any]] = (request.results ?? []).compactMap { item in
            guard let candidate = item.topCandidates(1).first else { return nil }
            return ["text": candidate.string,
                    "bbox": ocrRegion(item.boundingBox),
                    "confidence": Double(candidate.confidence)]
        }
        return ["status": lines.isEmpty ? "no_text" : "extracted", "lines": lines]
    } catch let error as NSError {
        return ["status": "failed", "lines": [],
                "error": "vision_error:\(error.domain):\(error.code)"]
    }
}

do {
    let input = FileHandle.standardInput.readDataToEndOfFile()
    guard let payload = try JSONSerialization.jsonObject(with: input) as? [String: Any],
          let path = payload["pdf_path"] as? String,
          let pages = payload["pages"] as? [Int],
          let ocrImages = payload["ocr_images"] as? [String: String],
          let document = PDFDocument(url: URL(fileURLWithPath: path)) else {
        throw NSError(domain: "invalid_input", code: 1)
    }
    var results: [[String: Any]] = []
    for number in pages {
        guard number > 0, number <= document.pageCount,
              let page = document.page(at: number - 1) else {
            throw NSError(domain: "invalid_page", code: number)
        }
        let native = extractNative(page)
        var result: [String: Any] = [
            "page_number": number,
            "page_rotation": page.rotation,
            "page_width_points": page.bounds(for: .cropBox).width,
            "page_height_points": page.bounds(for: .cropBox).height,
            "native_text": ["status": native.isEmpty ? "no_text" : "extracted",
                            "lines": native],
            "ocr_text": ["status": "not_run", "lines": []],
        ]
        if let image = ocrImages[String(number)] {
            result["ocr_text"] = extractOcr(image)
        }
        results.append(result)
    }
    let output: [String: Any] = [
        "schema": "skopos/pdf-document-macos-extract/v0.1",
        "page_count": document.pageCount,
        "platform": "macos",
        "pages": results,
    ]
    let encoded = try JSONSerialization.data(withJSONObject: output,
                                              options: [.sortedKeys, .fragmentsAllowed])
    FileHandle.standardOutput.write(encoded)
    FileHandle.standardOutput.write(Data("\n".utf8))
} catch let error as NSError {
    let output = ["schema": "skopos/pdf-document-macos-extract/v0.1",
                  "error": "\(error.domain):\(error.code)"]
    if let encoded = try? JSONSerialization.data(withJSONObject: output) {
        FileHandle.standardOutput.write(encoded)
        FileHandle.standardOutput.write(Data("\n".utf8))
    }
    exit(1)
}
