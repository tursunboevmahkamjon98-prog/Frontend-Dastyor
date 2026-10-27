import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_pdfview/flutter_pdfview.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/utils/web_pdf_opener.dart';
import '../../l10n/gen/app_localizations.dart';















class PdfViewerBody extends StatefulWidget {
  const PdfViewerBody({super.key, required this.bytes, this.onPageInfo});

  final Uint8List bytes;
  final void Function(int currentPage, int pageCount)? onPageInfo;

  @override
  State<PdfViewerBody> createState() => _PdfViewerBodyState();
}

class _PdfViewerBodyState extends State<PdfViewerBody> {
  String? _path;
  String? _error;
  int _pageCount = 0;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    if (kIsWeb) {
      
      
      
      openPdfInNewTab(widget.bytes);
    } else {
      _writeTempFile();
    }
  }

  Future<void> _writeTempFile() async {
    try {
      final dir = await getTemporaryDirectory();
      final file = File(
          '${dir.path}/preview_${DateTime.now().millisecondsSinceEpoch}.pdf');
      await file.writeAsBytes(widget.bytes, flush: true);
      if (mounted) setState(() => _path = file.path);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  void dispose() {
    
    
    
    
    if (_path != null) {
      File(_path!).delete().catchError((_) => File(_path!));
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    if (kIsWeb) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.picture_as_pdf_rounded,
                  size: 56, color: Colors.white70),
              const SizedBox(height: 16),
              Text(t.pdfWebOpenedHint,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70)),
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: () => openPdfInNewTab(widget.bytes),
                style: FilledButton.styleFrom(backgroundColor: AppColors.brand),
                icon: const Icon(Icons.open_in_new_rounded),
                label: Text(t.pdfWebOpenButton),
              ),
            ],
          ),
        ),
      );
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(t.errorGeneric,
              style: const TextStyle(color: Colors.white),
              textAlign: TextAlign.center),
        ),
      );
    }
    if (_path == null) {
      return const Center(
          child: CircularProgressIndicator(color: Colors.white));
    }
    return PDFView(
      filePath: _path!,
      enableSwipe: true,
      swipeHorizontal: false,
      autoSpacing: true,
      pageFling: true,
      onRender: (pages) {
        setState(() => _pageCount = pages ?? 0);
        widget.onPageInfo?.call(_currentPage, _pageCount);
      },
      onPageChanged: (page, total) {
        setState(() => _currentPage = page ?? 0);
        widget.onPageInfo?.call(_currentPage, _pageCount);
      },
      onError: (e) => setState(() => _error = e.toString()),
    );
  }
}











class PdfPreviewScreen extends StatefulWidget {
  const PdfPreviewScreen({super.key, required this.bytes, required this.title});

  final Uint8List bytes;
  final String title;

  @override
  State<PdfPreviewScreen> createState() => _PdfPreviewScreenState();
}

class _PdfPreviewScreenState extends State<PdfPreviewScreen> {
  int _currentPage = 0;
  int _pageCount = 0;
  bool _saving = false;

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      
      
      
      
      
      final safeTitle = widget.title
          .replaceAll(RegExp(r'[^\p{L}\p{N}\s-]', unicode: true), '')
          .trim();
      final fileName = safeTitle.isEmpty ? 'document.pdf' : '$safeTitle.pdf';
      final savedPath = await FilePicker.saveFile(
        fileName: fileName,
        bytes: widget.bytes,
        type: FileType.any,
      );
      if (!mounted) return;
      if (savedPath != null) {
        final t = AppLocalizations.of(context);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(t.materialSaved)));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: AppColors.brand,
        foregroundColor: Colors.white,
        title: Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          if (_pageCount > 0)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Center(child: Text('${_currentPage + 1} / $_pageCount')),
            ),
          if (_saving)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                    strokeWidth: 2.4, color: Colors.white),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.download_rounded),
              tooltip: t.download,
              onPressed: _save,
            ),
        ],
      ),
      body: PdfViewerBody(
        bytes: widget.bytes,
        onPageInfo: (current, total) => setState(() {
          _currentPage = current;
          _pageCount = total;
        }),
      ),
    );
  }
}
