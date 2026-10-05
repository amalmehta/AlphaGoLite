import AppKit
import SwiftUI

/// Small feedback form. Entries are appended, one JSON object per line, to
/// ~/Library/Application Support/AlphaGo Lite/feedback.jsonl — nothing is sent anywhere.
struct FeedbackView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var kind = "Idea"
    @State private var text = ""
    @State private var saved = false

    static var fileURL: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("AlphaGo Lite", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("feedback.jsonl")
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Send Feedback").font(.title3.bold())
            Picker("Type", selection: $kind) {
                ForEach(["Idea", "Bug", "Other"], id: \.self) { Text($0) }
            }
            .pickerStyle(.segmented)
            TextEditor(text: $text)
                .font(.body)
                .frame(minHeight: 120)
                .overlay(RoundedRectangle(cornerRadius: 6).stroke(.secondary.opacity(0.3)))
            Text("Saved on this Mac only, in Application Support/AlphaGo Lite/feedback.jsonl.")
                .font(.caption).foregroundStyle(.secondary)
            HStack {
                if saved {
                    Label("Saved", systemImage: "checkmark.circle.fill").foregroundStyle(.green)
                    Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([Self.fileURL]) }
                }
                Spacer()
                Button("Close") { dismiss() }.keyboardShortcut(.cancelAction)
                Button("Save") { save() }
                    .keyboardShortcut(.defaultAction)
                    .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
        .padding(20)
        .frame(width: 420)
    }

    func save() {
        let entry: [String: String] = [
            "date": ISO8601DateFormatter().string(from: Date()),
            "type": kind,
            "text": text,
            "version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "dev",
        ]
        guard var line = try? JSONSerialization.data(withJSONObject: entry, options: [.sortedKeys]) else { return }
        line.append(0x0A)
        let url = Self.fileURL
        if let h = try? FileHandle(forWritingTo: url) {
            h.seekToEndOfFile(); h.write(line); try? h.close()
        } else {
            try? line.write(to: url)
        }
        text = ""
        saved = true
    }
}
