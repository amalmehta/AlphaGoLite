// Renders Resources/AppIcon.icns: a small Go board with a few stones.
//   swift scripts/make_icon.swift
import AppKit

func render(_ px: Int) -> Data {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                               bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let s = CGFloat(px)
    let inset = s * 0.09
    let board = NSRect(x: inset, y: inset, width: s - 2 * inset, height: s - 2 * inset)
    NSColor(red: 0.86, green: 0.70, blue: 0.45, alpha: 1).setFill()
    NSBezierPath(roundedRect: board, xRadius: s * 0.18, yRadius: s * 0.18).fill()
    let n = 5, cell = board.width / CGFloat(n + 1)
    NSColor(white: 0, alpha: 0.7).setStroke()
    for i in 1...n {
        let d = board.minX + CGFloat(i) * cell
        let p = NSBezierPath(); p.lineWidth = max(1, s * 0.012)
        p.move(to: NSPoint(x: d, y: board.minY + cell)); p.line(to: NSPoint(x: d, y: board.maxY - cell))
        p.move(to: NSPoint(x: board.minX + cell, y: d)); p.line(to: NSPoint(x: board.maxX - cell, y: d))
        p.stroke()
    }
    let stones: [(Int, Int, Bool)] = [(2, 3, true), (3, 3, false), (3, 2, true), (4, 4, false), (2, 2, false), (3, 4, true)]
    for (c, r, black) in stones {
        let center = NSPoint(x: board.minX + CGFloat(c) * cell, y: board.minY + CGFloat(r) * cell)
        let rad = cell * 0.46
        let rect = NSRect(x: center.x - rad, y: center.y - rad, width: 2 * rad, height: 2 * rad)
        let g = black ? NSGradient(starting: NSColor(white: 0.45, alpha: 1), ending: NSColor(white: 0.05, alpha: 1))!
                      : NSGradient(starting: .white, ending: NSColor(white: 0.78, alpha: 1))!
        g.draw(in: NSBezierPath(ovalIn: rect), relativeCenterPosition: NSPoint(x: -0.35, y: 0.35))
    }
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:])!
}

let set = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("AppIcon.iconset")
try? FileManager.default.removeItem(at: set)
try! FileManager.default.createDirectory(at: set, withIntermediateDirectories: true)
for base in [16, 32, 128, 256, 512] {
    try! render(base).write(to: set.appendingPathComponent("icon_\(base)x\(base).png"))
    try! render(base * 2).write(to: set.appendingPathComponent("icon_\(base)x\(base)@2x.png"))
}
let p = Process()
p.executableURL = URL(fileURLWithPath: "/usr/bin/iconutil")
p.arguments = ["-c", "icns", set.path, "-o", "Resources/AppIcon.icns"]
try! p.run(); p.waitUntilExit()
print("wrote Resources/AppIcon.icns")
