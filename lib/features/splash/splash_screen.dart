import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../widgets/brand/dastyor_logo.dart';




class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: AppColors.white,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DastyorMark(height: 96),
            SizedBox(height: 24),
            CircularProgressIndicator(color: AppColors.brand),
          ],
        ),
      ),
    );
  }
}
