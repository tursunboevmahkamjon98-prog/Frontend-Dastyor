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
import '../../widgets/auth_hero_header.dart';
import '../../widgets/auth_page_width.dart';
import '../../widgets/loading_button.dart';
import '../../widgets/motion.dart';




class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  bool _loading = false;
  bool _obscure = true;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final phone = Validators.normalizePhone(_phoneCtrl.text);
    setState(() => _loading = true);
    try {
      await context.read<AuthProvider>().sendRegisterCode(phone);
      if (!mounted) return;
      context.push(Routes.registerOtp, extra: {
        'fullName': _nameCtrl.text.trim(),
        'phone': phone,
        'password': _passwordCtrl.text,
      });
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
    
    
    
    
    return Theme(
      data: AppTheme.light(),
      child: Scaffold(
        backgroundColor: AppColors.white,
        body: SafeArea(
          bottom: false,
          
          
          
          child: SingleChildScrollView(
            child: AuthPageWidth(
              child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AuthHeroHeader(
                  title: t.createAccount,
                  subtitle: t.createAccountSubtitle,
                  showBack: true,
                ),
                StaggerIn(
                  delayMs: 80,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          TextFormField(
                            controller: _nameCtrl,
                            decoration: InputDecoration(
                              labelText: t.fullName,
                              hintText: t.fullNameHint,
                              prefixIcon:
                                  const Icon(Icons.person_outline_rounded),
                            ),
                            validator: (v) => Validators.isValidName(v ?? '')
                                ? null
                                : t.errorNameShort,
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _phoneCtrl,
                            keyboardType: TextInputType.phone,
                            decoration: InputDecoration(
                              labelText: t.phoneNumber,
                              hintText: '+992 XX XXX XXXX',
                              prefixIcon: const Icon(Icons.phone_outlined),
                            ),
                            validator: (v) => Validators.isValidPhone(v ?? '')
                                ? null
                                : t.errorPhoneInvalid,
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _passwordCtrl,
                            obscureText: _obscure,
                            decoration: InputDecoration(
                              labelText: t.password,
                              prefixIcon:
                                  const Icon(Icons.lock_outline_rounded),
                              suffixIcon: IconButton(
                                icon: Icon(_obscure
                                    ? Icons.visibility_off_rounded
                                    : Icons.visibility_rounded),
                                onPressed: () =>
                                    setState(() => _obscure = !_obscure),
                              ),
                            ),
                            validator: (v) =>
                                Validators.isValidPassword(v ?? '')
                                    ? null
                                    : t.errorPasswordShort,
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _confirmCtrl,
                            obscureText: _obscure,
                            decoration: InputDecoration(
                              labelText: t.confirmPassword,
                              prefixIcon:
                                  const Icon(Icons.lock_outline_rounded),
                            ),
                            validator: (v) => v == _passwordCtrl.text
                                ? null
                                : t.errorPasswordMismatch,
                          ),
                          const SizedBox(height: 24),
                          LoadingButton(
                              label: t.sendCode,
                              loading: _loading,
                              onPressed: _submit),
                          const SizedBox(height: 20),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(t.alreadyHaveAccount,
                                  style: const TextStyle(
                                      color: AppColors.inkSoft)),
                              TextButton(
                                  
                                  
                                  
                                  
                                  
                                  onPressed: () => context.canPop()
                                      ? context.pop()
                                      : context.go(Routes.login),
                                  child: Text(t.login)),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
            ),
          ),
        ),
      ),
    );
  }
}
