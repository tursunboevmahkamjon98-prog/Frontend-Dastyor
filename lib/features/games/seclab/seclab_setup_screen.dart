import 'package:flutter/material.dart';
import '../../../l10n/gen/app_localizations.dart';
import '../widgets/game_setup_form.dart';
import 'seclab_game_screen.dart';




class SecLabSetupScreen extends StatelessWidget {
  const SecLabSetupScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: const Color(0xFF070C1A),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -1),
            radius: 1.3,
            colors: [Color(0xFF1E3A5F), Color(0xFF12203C), Color(0xFF070C1A)],
          ),
        ),
        child: Stack(
          children: [
            GameSetupForm(
              title: t.gameSecLabName,
              subtitle: t.gameSecLabSubtitle,
              startLabel: t.gameSecLabStart,
              accent: const Color(0xFF38BDF8),
              defaultSubject: 'Химия',
              roundChoices: const [5, 10, 15],
              roundsLabel: t.questionCountLabel,
              onReady: (questions) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(
                    
                    
                    
                    
                    
                    
                    builder: (gameContext) => SecLabGameScreen(
                      questions: questions,
                      onExit: () => Navigator.of(gameContext).pop(),
                    ),
                  ),
                );
              },
            ),
            SafeArea(
              child: Align(
                alignment: Alignment.topLeft,
                child: IconButton(
                  icon: const Icon(Icons.arrow_back_rounded, color: Colors.white70),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
