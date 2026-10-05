import GoEngine
import SwiftUI

/// What to draw on top of the stones.
struct BoardOverlay {
    /// Visit counts per move (length 82); drawn as a heat map with win rates on the top moves.
    var visits: [Double]? = nil
    /// Win rate (0...1, for the player to move) per point, shown on the top moves.
    var winrates: [Int: Double] = [:]
    var bestMove: Int? = nil
    /// Principal variation, drawn as numbered ghost stones.
    var variation: [Int] = []
    /// Territory owner per point (1 black, -1 white) at game end.
    var ownership: [Int8]? = nil
}

struct BoardView: View {
    let position: Position
    var lastMove: Int? = nil
    var overlay = BoardOverlay()
    var interactive = false
    var onPlay: ((Int) -> Void)? = nil

    @State private var hover: Int? = nil

    static let wood = Color(red: 0.86, green: 0.70, blue: 0.45)
    static let stars = [20, 24, 40, 56, 60]

    var body: some View {
        GeometryReader { geo in
            let side = min(geo.size.width, geo.size.height)
            let cell = side / 10
            let origin = CGPoint(x: (geo.size.width - side) / 2 + cell, y: (geo.size.height - side) / 2 + cell)
            Canvas { ctx, _ in
                draw(ctx, origin: origin, cell: cell, side: side, offset: CGPoint(x: (geo.size.width - side) / 2, y: (geo.size.height - side) / 2))
            }
            .contentShape(Rectangle())
            .onContinuousHover { phase in
                if case .active(let p) = phase, interactive { hover = point(at: p, origin: origin, cell: cell) } else { hover = nil }
            }
            .onTapGesture(coordinateSpace: .local) { p in
                guard interactive, let m = point(at: p, origin: origin, cell: cell), position.isLegal(m) else { return }
                onPlay?(m)
            }
        }
        .aspectRatio(1, contentMode: .fit)
        .accessibilityLabel("Go board")
    }

    func point(at p: CGPoint, origin: CGPoint, cell: CGFloat) -> Int? {
        let c = Int(((p.x - origin.x) / cell).rounded()), r = Int(((p.y - origin.y) / cell).rounded())
        guard (0..<9).contains(r), (0..<9).contains(c) else { return nil }
        return r * 9 + c
    }

    func center(_ m: Int, _ origin: CGPoint, _ cell: CGFloat) -> CGPoint {
        CGPoint(x: origin.x + CGFloat(m % 9) * cell, y: origin.y + CGFloat(m / 9) * cell)
    }

    func circle(_ c: CGPoint, _ r: CGFloat) -> Path {
        Path(ellipseIn: CGRect(x: c.x - r, y: c.y - r, width: 2 * r, height: 2 * r))
    }

    func draw(_ ctx: GraphicsContext, origin: CGPoint, cell: CGFloat, side: CGFloat, offset: CGPoint) {
        let rect = CGRect(x: offset.x, y: offset.y, width: side, height: side)
        ctx.fill(Path(roundedRect: rect, cornerRadius: side * 0.015), with: .color(Self.wood))

        // grid, star points, coordinates
        var grid = Path()
        for i in 0..<9 {
            let d = CGFloat(i) * cell
            grid.move(to: CGPoint(x: origin.x, y: origin.y + d)); grid.addLine(to: CGPoint(x: origin.x + 8 * cell, y: origin.y + d))
            grid.move(to: CGPoint(x: origin.x + d, y: origin.y)); grid.addLine(to: CGPoint(x: origin.x + d, y: origin.y + 8 * cell))
        }
        ctx.stroke(grid, with: .color(.black.opacity(0.75)), lineWidth: max(1, cell * 0.02))
        for s in Self.stars { ctx.fill(circle(center(s, origin, cell), cell * 0.08), with: .color(.black.opacity(0.8))) }
        let font = Font.system(size: cell * 0.26, weight: .medium)
        for i in 0..<9 {
            let col = Text(String(Array("ABCDEFGHJ")[i])).font(font).foregroundColor(.black.opacity(0.55))
            ctx.draw(col, at: CGPoint(x: origin.x + CGFloat(i) * cell, y: origin.y - cell * 0.62))
            ctx.draw(col, at: CGPoint(x: origin.x + CGFloat(i) * cell, y: origin.y + 8 * cell + cell * 0.62))
            let row = Text("\(9 - i)").font(font).foregroundColor(.black.opacity(0.55))
            ctx.draw(row, at: CGPoint(x: origin.x - cell * 0.62, y: origin.y + CGFloat(i) * cell))
            ctx.draw(row, at: CGPoint(x: origin.x + 8 * cell + cell * 0.62, y: origin.y + CGFloat(i) * cell))
        }

        // territory
        if let own = overlay.ownership {
            for p in 0..<81 where position.board[p] == 0 && own[p] != 0 {
                let c = center(p, origin, cell)
                let sq = CGRect(x: c.x - cell * 0.15, y: c.y - cell * 0.15, width: cell * 0.3, height: cell * 0.3)
                ctx.fill(Path(sq), with: .color(own[p] == 1 ? .black.opacity(0.8) : .white.opacity(0.9)))
            }
        }

        // search heat map (under the stones)
        if let visits = overlay.visits {
            let maxV = visits[0..<81].max() ?? 0
            if maxV > 0 {
                for p in 0..<81 where visits[p] > 0 && position.board[p] == 0 {
                    let f = visits[p] / maxV
                    let r = cell * (0.18 + 0.27 * sqrt(f))
                    let color: Color = p == overlay.bestMove ? Color(red: 0.1, green: 0.55, blue: 0.95) : Color(red: 0.2, green: 0.45, blue: 0.9)
                    ctx.fill(circle(center(p, origin, cell), r), with: .color(color.opacity(0.25 + 0.6 * f)))
                }
            }
        }

        // stones
        for p in 0..<81 where position.board[p] != 0 {
            drawStone(ctx, center(p, origin, cell), cell, black: position.board[p] == 1, alpha: 1)
        }
        if let m = lastMove, m < 81, position.board[m] != 0 {
            ctx.stroke(circle(center(m, origin, cell), cell * 0.2),
                       with: .color(position.board[m] == 1 ? .white : .black), lineWidth: max(1.5, cell * 0.05))
        }

        // win rates on the top moves
        for (m, w) in overlay.winrates where m < 81 && position.board[m] == 0 {
            let t = Text(String(format: "%.0f", w * 100)).font(.system(size: cell * 0.26, weight: .bold)).foregroundColor(.white)
            ctx.draw(t, at: center(m, origin, cell))
        }

        // principal variation
        var toPlay = position.toPlay
        for (i, m) in overlay.variation.prefix(6).enumerated() {
            if m < 81 && position.board[m] == 0 {
                let c = center(m, origin, cell)
                drawStone(ctx, c, cell, black: toPlay == .black, alpha: 0.45)
                ctx.draw(Text("\(i + 1)").font(.system(size: cell * 0.3, weight: .bold))
                    .foregroundColor(toPlay == .black ? .white : .black), at: c)
            }
            toPlay = toPlay.opponent
        }

        // hover ghost
        if let h = hover, interactive, position.isLegal(h), position.board[h] == 0 {
            drawStone(ctx, center(h, origin, cell), cell, black: position.toPlay == .black, alpha: 0.4)
        }
    }

    func drawStone(_ ctx: GraphicsContext, _ c: CGPoint, _ cell: CGFloat, black: Bool, alpha: Double) {
        let r = cell * 0.47
        var shadowed = ctx
        if alpha == 1 { shadowed.addFilter(.shadow(color: .black.opacity(0.35), radius: cell * 0.05, x: cell * 0.03, y: cell * 0.04)) }
        let grad = Gradient(colors: black
            ? [Color(white: 0.45), Color(white: 0.05)]
            : [Color.white, Color(white: 0.78)])
        shadowed.fill(circle(c, r), with: .radialGradient(grad, center: CGPoint(x: c.x - r * 0.35, y: c.y - r * 0.35),
                                                         startRadius: 0, endRadius: r * 1.6))
        if alpha < 1 {
            ctx.fill(circle(c, r), with: .color(Self.wood.opacity(1 - alpha)))
        }
    }
}

/// Horizontal bar: black's win probability vs white's.
struct WinBar: View {
    /// Black's win probability 0...1
    let black: Double

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(Color(white: 0.93))
                Rectangle().fill(Color(white: 0.12)).frame(width: geo.size.width * black)
                HStack {
                    Text("Black \(Int((black * 100).rounded()))%").foregroundStyle(.white)
                    Spacer()
                    Text("White \(Int(((1 - black) * 100).rounded()))%").foregroundStyle(.black)
                }
                .font(.caption.monospacedDigit().bold())
                .padding(.horizontal, 8)
            }
        }
        .frame(height: 22)
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(.secondary.opacity(0.4)))
        .animation(.easeInOut(duration: 0.3), value: black)
        .accessibilityLabel("Black win probability \(Int(black * 100)) percent")
    }
}
