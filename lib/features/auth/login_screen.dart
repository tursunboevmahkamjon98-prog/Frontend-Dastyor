import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/routing/routes.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/validators.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/auth_page_width.dart';
import '../../widgets/auth_side_panel.dart';
import '../../widgets/loading_button.dart';
import '../../widgets/motion.dart';
import '../../widgets/brand/dastyor_logo.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _loading = false;
  bool _obscure = true;

  @override
  void dispose() {
    _phoneCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      final phone = Validators.normalizePhone(_phoneCtrl.text);
      final password = _passwordCtrl.text;
      
      
      
      
      
      
      await context
          .read<AuthProvider>()
          .login(phone: phone, password: password);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    
    
    
    
    
    
    final form = SingleChildScrollView(
      child: AuthPageWidth(child: _buildForm(context, t)),
    );
    return Theme(
      data: AppTheme.light(),
      child: Scaffold(
        backgroundColor: AppColors.white,
        body: SafeArea(
          bottom: false,
          
          
          
          
          
          child: !kIsWeb
              ? form
              : LayoutBuilder(
                  builder: (context, constraints) {
                    if (constraints.maxWidth < 900) return form;
                    return Row(
                      children: [
                        const Expanded(flex: 5, child: AuthSidePanel()),
                        Expanded(flex: 4, child: form),
                      ],
                    );
                  },
                ),
        ),
      ),
    );
  }

  InputDecoration _fieldDecoration({
    required String label,
    String? hint,
    required IconData icon,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: Icon(icon, color: AppColors.inkFaint),
      suffixIcon: suffixIcon,
      filled: true,
      fillColor: AppColors.surfaceMuted,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: BorderSide.none,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.brand, width: 1.5),
      ),
    );
  }

  Widget _buildForm(BuildContext context, AppLocalizations t) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 40, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              // Was a brand-red tile with the mark tinted flat white. The
              // real mark is a gradient and cannot be flattened, so this is
              // the brand sheet's white-plate treatment instead.
              const DastyorMark(height: 29, plate: true),
              const SizedBox(width: 12),
              const Text('Dastyor',
                  style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                      color: AppColors.ink)),
            ],
          ),
          const SizedBox(height: 20),
          Text(t.welcomeBackSubtitle,
              style: const TextStyle(fontSize: 15, color: AppColors.inkSoft)),
          const SizedBox(height: 28),
          StaggerIn(
            delayMs: 80,
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    controller: _phoneCtrl,
                    keyboardType: TextInputType.phone,
                    decoration: _fieldDecoration(
                      label: t.phoneNumber,
                      hint: '+992 XX XXX XXXX',
                      icon: Icons.phone_outlined,
                    ),
                    validator: (v) => Validators.isValidPhone(v ?? '')
                        ? null
                        : t.errorPhoneInvalid,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _passwordCtrl,
                    obscureText: _obscure,
                    decoration: _fieldDecoration(
                      label: t.password,
                      icon: Icons.lock_outline_rounded,
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscure
                              ? Icons.visibility_off_rounded
                              : Icons.visibility_rounded,
                          color: AppColors.inkFaint,
                        ),
                        onPressed: () =>
                            setState(() => _obscure = !_obscure),
                      ),
                    ),
                    validator: (v) =>
                        (v == null || v.isEmpty) ? t.errorRequired : null,
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () => context.push(Routes.forgotPassword),
                      child: Text(t.forgotPassword),
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 52,
                    child: LoadingButton(
                        label: t.login, loading: _loading, onPressed: _submit),
                  ),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(t.dontHaveAccount,
                          style: const TextStyle(color: AppColors.inkSoft)),
                      TextButton(
                          onPressed: () => context.push(Routes.register),
                          child: Text(t.register)),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
