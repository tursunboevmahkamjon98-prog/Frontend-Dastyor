
import 'dart:html' as html;
import 'dart:typed_data';











void openPdfInNewTab(Uint8List bytes) {
  final blob = html.Blob([bytes], 'application/pdf');
  final url = html.Url.createObjectUrlFromBlob(blob);
  html.window.open(url, '_blank');
  
  
  
}
