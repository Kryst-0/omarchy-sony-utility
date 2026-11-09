import QtQuick
Canvas {
  id: root
  property color color: "white"
  property real iconSize: 24
  property real strokeWidth: 1.5
  implicitWidth: iconSize
  implicitHeight: iconSize
  onColorChanged: requestPaint()
  onWidthChanged: requestPaint()
  onHeightChanged: requestPaint()
  onPaint: {
    var c = getContext("2d")
    c.reset()
    c.scale(width / 24, height / 24)
    c.strokeStyle = color
    c.fillStyle = Qt.rgba(color.r, color.g, color.b, 0.08)
    c.lineWidth = strokeWidth
    c.lineCap = "round"
    c.lineJoin = "round"
    c.beginPath()
    c.moveTo(4, 14)
    c.lineTo(4, 11)
    c.bezierCurveTo(4, 0, 20, 0, 20, 11)
    c.lineTo(20, 14)
    c.stroke()
    c.beginPath()
    c.roundedRect(2.5, 12, 5, 9, 2, 2)
    c.roundedRect(16.5, 12, 5, 9, 2, 2)
    c.fill()
    c.stroke()
  }
}
