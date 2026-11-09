import QtQuick
import QtTest
import "../DeviceModel.js" as Model
TestCase {
 name:"SonyUtility"
 property string output:""
 property var devices:[{name:"WH-CH520",address:"00:11:22:33:44:55",connected:true}]
 readonly property var selected:Model.bluetoothDevice(devices,output)
 function test_default_output() {output="bluez_output.00_11_22_33_44_55.1";compare(selected.address,"00:11:22:33:44:55");output="alsa_output.internal";compare(selected,null)}
 function test_other_sony_not_claimed() {compare(Model.bluetoothDevice([{name:"WH-CH720N",address:"00:11:22:33:44:55",connected:true}],"bluez_output.00_11_22_33_44_55.1"),null)}
 function test_disconnected_hidden() {compare(Model.bluetoothDevice([{name:"WH-CH520",address:"00:11:22:33:44:55",connected:false}],"bluez_output.00_11_22_33_44_55.1"),null)}
 function test_invalid_native_values_hidden() {compare(Model.validState({preset:999,bands:[99],dsee:1,priority:8}),({}))}
 function test_five_bands_plus_clear_bass() {compare(Model.validState({bands:[-10,0,1,2,3,10],preset:160}).bands.length,6)}
 function test_untrusted_labels_preserved() {var label='<img src="https://example.invalid/x">';compare(Model.validState({presets:[{value:160,name:label}]}).presets[0].name,label)}
}
