import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Bluetooth
import Quickshell.Services.Pipewire
import qs.Ui
import qs.Commons
import qs.Commons as Commons
import "DeviceModel.js" as Model

Panel {
  id: root
  moduleName: "krysto.sony-utility"
  ipcTarget: moduleName
  manageIpc: false
  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }
  readonly property var sink: Pipewire.defaultAudioSink
  readonly property var devices: Bluetooth.devices ? Bluetooth.devices.values : []
  readonly property string sinkName: sink ? String(sink.name || "") : ""
  readonly property var bt: Model.bluetoothDevice(devices, sinkName)
  readonly property bool selected: !!bt
  readonly property string transport: "bluetooth"
  readonly property string address: bt ? String(bt.address) : ""
  readonly property string endpoint: address
  PwObjectTracker { objects: root.sink ? [root.sink] : [] }
  readonly property bool ready: selected && !!sink && !!sink.audio
  readonly property color foreground: bar ? bar.foreground : Commons.Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.55)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  property var state: ({})
  property string errorKey: ""
  property string resultKey: ""
  property var draftBands: [0,0,0,0,0,0]
  readonly property bool linkConfirmed: !!bt
  readonly property int battery: bt && bt.batteryAvailable ? Math.round(bt.battery * 100) : -1
  readonly property color iconColor: !linkConfirmed ? dim : battery >= 0 && battery <= 20 ? (bar ? bar.urgent : Commons.Color.urgent) : foreground
  visible: selected
  implicitWidth: visible ? button.implicitWidth : 0
  implicitHeight: button.implicitHeight
  onVisibleChanged: if (!visible) close()
  onEndpointChanged: {
    state = ({})
    bandsDebounce.stop()
    errorKey = ""
    resultKey = ""
    pendingRead = opened && selected
    if (pendingRead && !settingsProcess.running) Qt.callLater(readSettings)
  }
  onOpenedChanged: { if (opened && selected) readSettings(); else bandsDebounce.stop() }
  readonly property string helper: decodeURIComponent(Qt.resolvedUrl("control.py").toString().replace(/^file:\/\//, ""))
  property var request: ({})
  property string requestEndpoint: ""
  property bool pendingRead: false
  readonly property bool busy: settingsProcess.running && requestEndpoint === endpoint

  function errorFor(code) {
    if (code === "permission-denied") return "permissionDenied"
    if (code === "unconfirmed") return "notConfirmed"
    if (code === "rejected") return "rejected"
    if (code === "busy") return "busyError"
    return "unavailable"
  }
  function readSettings() { send("status", "", null) }
  function send(op, feature, value) {
    if (!selected || !opened) return
    if (settingsProcess.running) { if (op === "status") pendingRead = true; return }
    if (op === "set" && state[feature] === undefined) return
    pendingRead = false
    errorKey = ""
    resultKey = ""
    requestEndpoint = endpoint
    request = {op: op, transport: transport, address: address}
    if (op === "set") request = {op: op, transport: transport, address: address, feature: feature, value: value}
    settingsProcess.running = true
  }
  function setBand(index, value) {
    var copy = draftBands.slice()
    copy[index] = Math.round(value)
    draftBands = copy
  }
  function mute() { if (ready) sink.audio.muted = !sink.audio.muted }
  function changeVolume(delta) { if (ready) sink.audio.volume = Math.max(0,Math.min(1,sink.audio.volume + delta)) }

  Process {
    id: settingsProcess
    command: ["timeout", "35s", "/usr/bin/python3", root.helper, JSON.stringify(root.request)]
    stdout: StdioCollector {
      onStreamFinished: {
        if (root.requestEndpoint !== root.endpoint) return
        try {
          if (this.text.length > 16384) throw new Error("Oversize")
          var data = JSON.parse(this.text)
          if (!data.ok) { root.state=({}); root.errorKey=root.errorFor(data.error); return }
          root.state = Model.validState(data.state)
          if (root.state.bands) root.draftBands=root.state.bands.slice()
          if (Object.keys(root.state).length === 0) root.errorKey="unavailable"

        } catch(e) { root.state=({});root.errorKey="unavailable" }
      }
    }
    onExited: if (root.pendingRead && root.opened && root.selected) Qt.callLater(root.readSettings)
  }
  Timer {
    id: bandsDebounce
    interval: 400
    property string editEndpoint: ""
    onRunningChanged: if (running) editEndpoint=root.endpoint
    onTriggered: if (editEndpoint === root.endpoint && root.opened && !root.busy) root.send("set","bands",root.draftBands)
  }
  IpcHandler {
    target: root.ipcTarget
    function open(): void { root.open() }
    function close(): void { root.close() }
    function toggle(): void { root.toggle() }
    function status(): string { return JSON.stringify({visible:root.visible,transport:root.transport,output:root.sinkName,connected:root.linkConfirmed,battery:root.battery,features:Object.keys(root.state),busy:root.busy,error:root.errorKey}) }
  }
  property int phraseIndex: 0
  readonly property var phrases: [strings.t("phrase1"),strings.t("phrase2"),strings.t("phrase3"),strings.t("phrase4"),strings.t("phrase5"),strings.t("phrase6")]
  Timer { interval:3600; running:root.opened && root.visible; repeat:true; onTriggered:phraseSwap.restart() }
  SequentialAnimation {
    id: phraseSwap
    PropertyAnimation { target:hero; property:"metaOpacity"; to:0; duration:Style.duration(120); easing.type:Easing.OutCubic }
    ScriptAction { script:root.phraseIndex=(root.phraseIndex+1)%root.phrases.length }
    PropertyAnimation { target:hero; property:"metaOpacity"; to:1; duration:Style.duration(180); easing.type:Easing.OutCubic }
  }
  BarIconButton {
    id:button
    anchors.fill:parent
    bar:root.bar
    iconComponent:Component { Item { HeadphonesIcon { anchors.centerIn:parent;iconSize:Style.bar.iconCanvas;strokeWidth:1.2;color:root.iconColor } } }
    onPressed:function(b) { if (b===Qt.MiddleButton) root.mute();else root.toggle() }
    onWheelMoved:function(delta) { root.changeVolume(delta>0?0.05:-0.05) }
  }
  KeyboardPanel {
    id:panel
    anchorItem:button
    owner:root
    bar:root.bar
    open:root.opened && root.visible
    contentWidth:panel.fittedContentWidth(Style.space(420))
    contentHeight:panel.fittedContentHeight(column.implicitHeight,Style.space(700))
    focusTarget:keys
    PanelKeyCatcher {
      id:keys
      anchors.fill:parent
      blocked:true
      Keys.onEscapePressed:root.close()
      Flickable {
        anchors.fill:parent
        contentWidth:width
        contentHeight:column.implicitHeight
        clip:true
        boundsBehavior:Flickable.StopAtBounds
        ScrollBar.vertical:ScrollBar { policy:ScrollBar.AsNeeded }
        Column {
          id:column
          width:parent.width
          spacing:Style.space(12)
          PanelHero {
            id:hero
            title:"Sony WH-CH520"
            meta:root.phrases[root.phraseIndex]
            foreground:root.foreground
            fontFamily:root.fontFamily
            iconComponent:Component { HeadphonesIcon {iconSize:Style.space(38);color:root.foreground} }
            trailingControl:Component { PanelActionButton { iconText:"󰑐";tooltipText:strings.t("refresh");foreground:root.foreground;fontFamily:root.fontFamily;enabled:!root.busy;onClicked:root.readSettings() } }
          }
          Caption { text:"Bluetooth" }
          Caption { visible:!root.linkConfirmed; text:strings.t("linkUnknown");width:parent.width;wrapMode:Text.WordWrap }
          PanelSectionHeader {text:strings.t("batteryTitle");foreground:root.foreground;fontFamily:root.fontFamily}
          RowLayout {
            width:parent.width
            spacing:Style.space(10)
            Caption { text:strings.t("headphones") }
            Rectangle {
              id:batteryTrack
              Layout.fillWidth:true
              implicitHeight:Style.space(6)
              radius:height/2
              color:Qt.darker(root.foreground,3.2)
              Rectangle {width:parent.width*Math.max(0,root.battery)/100;height:parent.height;radius:parent.radius;color:root.iconColor;Behavior on width {NumberAnimation {duration:Style.duration(240);easing.type:Easing.OutCubic}}}
            }
            Plain {text:root.battery>=0?Commons.I18n.formatNumber(root.battery)+"%":"—"}
          }
          PanelSeparator {foreground:root.foreground}
          RowLayout {
            width:parent.width
            Plain {Layout.fillWidth:true;text:root.ready?strings.t("volume").arg(Commons.I18n.formatNumber(Math.round(root.sink.audio.volume*100))):strings.t("waiting")}
            PanelActionButton {iconText:root.ready && root.sink.audio.muted?"󰝟":"󰕾";tooltipText:strings.t("mute");foreground:root.foreground;fontFamily:root.fontFamily;enabled:root.ready;onClicked:root.mute()}
          }
          Slider {
            id:volumeSlider
            width:parent.width
            implicitHeight:Style.space(28)
            from:0;to:1;stepSize:0.01
            enabled:root.ready
            value:root.ready?root.sink.audio.volume:0
            onMoved:if(root.ready)root.sink.audio.volume=value
            background:Rectangle {x:volumeSlider.leftPadding;y:volumeSlider.topPadding+volumeSlider.availableHeight/2-height/2;width:volumeSlider.availableWidth;height:Style.space(6);radius:height/2;color:Qt.darker(root.foreground,3.2);Rectangle {width:parent.width*volumeSlider.visualPosition;height:parent.height;radius:parent.radius;color:root.foreground}}
            handle:Rectangle {x:volumeSlider.leftPadding+volumeSlider.visualPosition*(volumeSlider.availableWidth-width);y:volumeSlider.topPadding+volumeSlider.availableHeight/2-height/2;width:Style.space(12);height:width;radius:width/2;color:root.foreground}
          }
          Caption {visible:root.busy||root.errorKey!==""||root.resultKey!=="";width:parent.width;wrapMode:Text.WordWrap;text:root.busy?strings.t("reading"):strings.t(root.errorKey||root.resultKey)}
          Column {
            visible:root.state.preset!==undefined
            width:parent.width
            spacing:Style.space(10)
            PanelSeparator {foreground:root.foreground}
            PanelSectionHeader {text:strings.t("eqTitle");foreground:root.foreground;fontFamily:root.fontFamily}
            Caption {text:strings.t("eqInternal");width:parent.width;wrapMode:Text.WordWrap}
            Flow {
              width:parent.width
              spacing:Style.space(6)
              Repeater {
                model:root.state.presets||[]
                ActionButton {required property var modelData;text:modelData.name||strings.t("presetNumber").arg(modelData.value);active:root.state.preset===modelData.value;enabled:!root.busy;onClicked:root.send("set","preset",modelData.value)}
              }
            }
            Column {
              visible:[160,161,162].indexOf(root.state.preset)>=0 && root.state.bands!==undefined
              width:parent.width
              spacing:Style.space(2)
              Repeater {
                model:["Clear Bass","400 Hz","1 kHz","2.5 kHz","6.3 kHz","16 kHz"]
                RowLayout {
                  required property string modelData
                  required property int index
                  width:parent.width
                  Caption {text:modelData;Layout.preferredWidth:Style.space(65)}
                  Slider {Layout.fillWidth:true;from:-10;to:10;stepSize:1;enabled:!root.busy;value:root.draftBands[index];onMoved:{root.setBand(index,value);if(!pressed)bandsDebounce.restart()}
                    onPressedChanged:if(!pressed)bandsDebounce.restart()}
                  Plain {Layout.preferredWidth:Style.space(25);text:Commons.I18n.formatNumber(root.draftBands[index])}
                }
              }
              Caption {text:strings.t("relativeLevels");width:parent.width;wrapMode:Text.WordWrap}
            }
          }
          Column {
            visible:root.state.dsee!==undefined || root.state.voice!==undefined || root.state.priority!==undefined
            width:parent.width
            spacing:Style.space(10)
            PanelSeparator {foreground:root.foreground}
            PanelSectionHeader {text:strings.t("modesTitle");foreground:root.foreground;fontFamily:root.fontFamily}
            ModeRow {visible:root.state.dsee!==undefined;width:parent.width;label:"DSEE";checked:root.state.dsee===true;onToggled:root.send("set","dsee",!root.state.dsee)}
            ModeRow {visible:root.state.voice!==undefined;width:parent.width;label:strings.t("voice");checked:root.state.voice===true;onToggled:root.send("set","voice",!root.state.voice)}
            Caption {visible:root.state.priority!==undefined;text:strings.t("priorityTitle")}
            RowLayout {
              visible:root.state.priority!==undefined
              width:parent.width
              spacing:Style.space(6)
              ActionButton {Layout.fillWidth:true;text:strings.t("quality");active:root.state.priority===0;enabled:!root.busy;onClicked:root.send("set","priority",0)}
              ActionButton {Layout.fillWidth:true;text:strings.t("stability");active:root.state.priority===1;enabled:!root.busy;onClicked:root.send("set","priority",1)}
            }
          }
          Caption {visible:root.state.multipoint!==undefined;text:root.state.multipoint===true?strings.t("multipointOn"):strings.t("multipointOff");width:parent.width;wrapMode:Text.WordWrap}
          Caption {visible:root.state.firmware!==undefined;text:strings.t("firmware").arg(root.state.firmware||"")}
          Caption {width:parent.width;wrapMode:Text.WordWrap;text:strings.t("phoneFeatures")}

        }
      }
    }
  }
  component Plain:Text {textFormat:Text.PlainText;color:root.foreground;font.family:root.fontFamily;font.pixelSize:Style.font.body}
  component Caption:Plain {color:root.dim;font.pixelSize:Style.font.bodySmall}
  component ActionButton:Button {foreground:root.foreground;fontFamily:root.fontFamily;fontSize:Style.font.bodySmall;bordered:true;focusable:true}
  component ModeRow:RowLayout {
    id:modeRow
    property string label:""
    property bool checked:false
    signal toggled()
    Plain {Layout.fillWidth:true;text:modeRow.label}
    ToggleSwitch {foreground:root.foreground;checked:modeRow.checked;busy:root.busy;onToggled:modeRow.toggled()}
  }
}
