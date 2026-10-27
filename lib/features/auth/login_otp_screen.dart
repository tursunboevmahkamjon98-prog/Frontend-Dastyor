import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/auth_page_width.dart';
import '../../widgets/loading_button.dart';





class LoginOtpScreen extends StatefulWidget {
  const LoginOtpScreen({super.key, required this.args});

  final Map<String, String> args;

  @override
  State<LoginOtpScreen> createState() => _LoginOtpScreenState();
}

class _LoginOtpScreenState extends State<LoginOtpScreen> {
  final _codeCtrl = TextEditingController();
  bool _loading = false;
  bool _resending = false;
  Timer? _timer;
  int _secondsLeft = 60;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  void _startTimer() {
    _timer?.cancel();
    setState(() => _secondsLeft = 60);
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_secondsLeft <= 1) {
        timer.cancel();
        setState(() => _secondsLeft = 0);
      } else {
        setState(() => _secondsLeft -= 1);
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _resend() async {
    setState(() => _resending = true);
    try {
      await context.read<AuthProvider>().loginSendCode(
            phone: widget.args['phone']!,
            password: widget.args['password']!,
          );
      
      
      
      if (mounted) _startTimer();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _resending = false);
    }
  }

  Future<void> _verify() async {
    if (_codeCtrl.text.trim().isEmpty) return;
    setState(() => _loading = true);
    try {
      await context.read<AuthProvider>().loginVerify(
            phone: widget.args['phone']!,
            code: _codeCtrl.text.trim(),
          );
      
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: AuthPageWidth(
            child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(t.otpTitle,
                  style: Theme.of(context)
                      .textTheme
                      .headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              Text('${t.otpSubtitle} ${widget.args['phone']}',
                  style: const TextStyle(color: AppColors.inkSoft)),
              const SizedBox(height: 32),
              TextField(
                controller: _codeCtrl,
                keyboardType: TextInputType.number,
                maxLength: 6,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700, letterSpacing: 8),
                decoration: const InputDecoration(counterText: ''),
              ),
              const SizedBox(height: 8),
              Center(
                child: _secondsLeft > 0
                    ? Text(t.otpResendIn(_secondsLeft),
                        style: const TextStyle(color: AppColors.inkSoft))
                    : TextButton(onPressed: _resending ? null : _resend, child: Text(t.otpResend)),
              ),
              const SizedBox(height: 24),
              LoadingButton(label: t.otpVerify, loading: _loading, onPressed: _verify),
            ],
            ),
          ),
        ),
      ),
    );
  }
}
