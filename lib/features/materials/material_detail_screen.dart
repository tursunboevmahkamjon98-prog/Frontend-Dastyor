import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart' hide MaterialType;
import 'package:go_router/go_router.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../models/material_item.dart';
import '../../models/material_type.dart';
import '../../services/materials_service.dart';
import 'konspekt_edit_screen.dart';
import 'pdf_preview_screen.dart';

enum _DownloadFormat { docx, pdf, pptx }








class MaterialDetailScreen extends StatefulWidget {
  const MaterialDetailScreen(
      {super.key, required this.type, required this.id, this.initial});

  
  
  
  
  
  
  
  
  
  final MaterialType type;
  final String id;
  final MaterialItem? initial;

  @override
  State<MaterialDetailScreen> createState() => _MaterialDetailScreenState();
}

class _MaterialDetailScreenState extends State<MaterialDetailScreen> {
  final _materialsService = MaterialsService();
  _DownloadFormat? _downloading;
  bool _favoriteBusy = false;
  bool _deleting = false;
  bool _loading = false;
  ApiException? _loadError;

  
  
  
  MaterialItem? item;

  
  
  Uint8List? _pdfBytes;
  ApiException? _pdfError;
  bool _pdfFetching = false;
  int _pdfCurrentPage = 0;
  int _pdfPageCount = 0;

  @override
  void initState() {
    super.initState();
    item = widget.initial;
    if (item == null) {
      _fetch();
    } else {
      _maybeFetchPdf();
    }
  }

  Future<void> _fetch() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final fetched = await _materialsService.getOne(widget.type, widget.id);
      if (mounted) setState(() => item = fetched);
      _maybeFetchPdf();
    } on ApiException catch (e) {
      if (mounted) setState(() => _loadError = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _maybeFetchPdf() async {
    final current = item;
    if (current == null || current.decodedContent == null) return;
    if (_pdfBytes != null || _pdfFetching) return;
    setState(() {
      _pdfFetching = true;
      _pdfError = null;
    });
    try {
      final bytes = await _materialsService.downloadPdf(current);
      if (mounted) setState(() => _pdfBytes = bytes);
    } on ApiException catch (e) {
      if (mounted) setState(() => _pdfError = e);
    } finally {
      if (mounted) setState(() => _pdfFetching = false);
    }
  }

  Future<void> _toggleFavorite() async {
    final current = item!;
    final newValue = !current.isFavorite;
    setState(() => _favoriteBusy = true);
    try {
      await _materialsService.setFavorite(current.type, current.id, newValue);
      if (mounted) {
        setState(() => item = current.copyWith(isFavorite: newValue));
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _favoriteBusy = false);
    }
  }

  Future<void> _confirmDelete() async {
    final t = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(t.deleteConfirmTitle),
        content: Text(t.deleteConfirmMessage),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(t.cancel)),
          TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(t.delete)),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _deleting = true);
    try {
      await _materialsService.delete(item!.type, item!.id);
      if (mounted) context.pop();
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _deleting = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    }
  }

  
  
  
  
  Future<void> _openEdit() async {
    final current = item;
    if (current == null) return;
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => KonspektEditScreen(item: current)),
    );
    if (saved == true && mounted) {
      setState(() {
        _pdfBytes = null;
        _pdfPageCount = 0;
        _pdfCurrentPage = 0;
      });
      await _fetch();
      if (mounted) {
        final t = AppLocalizations.of(context);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(t.changesSaved)));
      }
    }
  }

  
  
  Future<void> _download(_DownloadFormat format) async {
    final current = item!;
    setState(() => _downloading = format);
    try {
      final bytes = switch (format) {
        _DownloadFormat.docx => await _materialsService.downloadDocx(current),
        _DownloadFormat.pptx => await _materialsService.downloadPptx(current),
        _DownloadFormat.pdf =>
          _pdfBytes ?? await _materialsService.downloadPdf(current),
      };
      if (!mounted) return;
      final ext = format.name;
      
      
      
      
      
      final safeTitle = current.title
          .replaceAll(RegExp(r'[^\p{L}\p{N}\s-]', unicode: true), '')
          .trim();
      final fileName = safeTitle.isEmpty ? 'material.$ext' : '$safeTitle.$ext';
      final savedPath = await FilePicker.saveFile(
        fileName: fileName,
        bytes: bytes,
        type: FileType.any,
      );
      if (!mounted) return;
      if (savedPath != null) {
        final t = AppLocalizations.of(context);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(t.materialSaved)));
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _downloading = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);

    if (this.item == null) {
      return Scaffold(
        appBar: AppBar(),
        body: Center(
          child: _loading
              ? const CircularProgressIndicator(color: AppColors.brand)
              : Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                          _loadError != null
                              ? messageFor(context, _loadError!)
                              : t.generationFailed,
                          textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      OutlinedButton(onPressed: _fetch, child: Text(t.retry)),
                    ],
                  ),
                ),
        ),
      );
    }

    final item = this.item!;
    final hasContent = item.decodedContent != null;
    return Scaffold(
      backgroundColor: hasContent && _pdfBytes != null ? Colors.black : null,
      appBar: AppBar(
        title: Text(item.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          if (_pdfPageCount > 0)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Center(
                  child: Text('${_pdfCurrentPage + 1} / $_pdfPageCount')),
            ),
          if (_favoriteBusy)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 12),
              child: SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                    strokeWidth: 2.2, color: AppColors.white),
              ),
            )
          else
            IconButton(
              icon: Icon(item.isFavorite
                  ? Icons.star_rounded
                  : Icons.star_outline_rounded),
              tooltip: item.isFavorite ? t.favoriteRemove : t.favoriteAdd,
              onPressed: _toggleFavorite,
            ),
          if (_deleting)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 12),
              child: SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                    strokeWidth: 2.2, color: AppColors.white),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded),
              tooltip: t.delete,
              onPressed: _confirmDelete,
            ),
          if (hasContent && item.type == MaterialType.konspekt)
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              tooltip: t.edit,
              onPressed: _openEdit,
            ),
          if (hasContent)
            if (_downloading != null)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2.4, color: AppColors.white),
                ),
              )
            else
              PopupMenuButton<_DownloadFormat>(
                icon: const Icon(Icons.download_rounded),
                onSelected: _download,
                itemBuilder: (context) => [
                  
                  
                  
                  
                  if (item.type == MaterialType.prezentatsiya)
                    PopupMenuItem(
                        value: _DownloadFormat.pptx,
                        child: Text(t.downloadPptx)),
                  PopupMenuItem(
                      value: _DownloadFormat.docx, child: Text(t.downloadDocx)),
                  PopupMenuItem(
                      value: _DownloadFormat.pdf, child: Text(t.downloadPdf)),
                ],
              ),
        ],
      ),
      body: !hasContent
          ? Center(child: Text(t.generationFailed))
          : _pdfError != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(messageFor(context, _pdfError!),
                            textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        OutlinedButton(
                            onPressed: _maybeFetchPdf, child: Text(t.retry)),
                      ],
                    ),
                  ),
                )
              : _pdfBytes == null
                  ? const Center(
                      child: CircularProgressIndicator(color: AppColors.brand))
                  : PdfViewerBody(
                      bytes: _pdfBytes!,
                      onPageInfo: (current, total) => setState(() {
                        _pdfCurrentPage = current;
                        _pdfPageCount = total;
                      }),
                    ),
      
      
      
      
      floatingActionButton:
          (hasContent && item.type == MaterialType.prezentatsiya)
              ? FloatingActionButton.extended(
                  onPressed: _downloading != null
                      ? null
                      : () => _download(_DownloadFormat.pptx),
                  backgroundColor: AppColors.brand,
                  foregroundColor: AppColors.white,
                  icon: _downloading == _DownloadFormat.pptx
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.2, color: AppColors.white),
                        )
                      : const Icon(Icons.slideshow_rounded),
                  label: Text(t.downloadPptx),
                )
              : null,
    );
  }
}
