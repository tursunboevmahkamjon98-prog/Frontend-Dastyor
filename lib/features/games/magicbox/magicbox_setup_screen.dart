import 'package:flutter/material.dart';
import '../../../l10n/gen/app_localizations.dart';
import '../widgets/game_setup_form.dart';
import 'magicbox_game_screen.dart';
import 'magicbox_logic.dart';




class MagicBoxSetupScreen extends StatelessWidget {
  const MagicBoxSetupScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: const Color(0xFF1B0F3A),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.7),
            radius: 1.4,
            colors: [Color(0xFF4C1D95), Color(0xFF2E1065), Color(0xFF1B0F3A)],
          ),
        ),
        child: Stack(
          children: [
            GameSetupForm(
              title: t.gameMagicBoxName,
              subtitle: t.gameMagicBoxSubtitle,
              startLabel: t.gameStart,
              accent: const Color(0xFFA855F7),
              
              
              questionsPerRound: kBoxCount,
              roundChoices: const [5, 8, 10],
              roundsLabel: t.gameRoundsLabel,
              onReady: (questions) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(
                    
                    
                    
                    
                    
                    
                    builder: (gameContext) => MagicBoxGameScreen(
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
