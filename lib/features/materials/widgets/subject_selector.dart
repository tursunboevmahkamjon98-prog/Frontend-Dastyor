import 'package:flutter/material.dart';
import '../../../core/constants/subject_identity.dart';
import '../../../core/theme/app_colors.dart';
import '../../../l10n/gen/app_localizations.dart';



class SubjectSelector extends StatefulWidget {
  final SubjectIdentity? initialSubject;
  final ValueChanged<SubjectIdentity> onSubjectChanged;
  final bool showTemplateCount;
  final int? templateCount;

  const SubjectSelector({
    super.key,
    this.initialSubject,
    required this.onSubjectChanged,
    this.showTemplateCount = true,
    this.templateCount,
  });

  @override
  State<SubjectSelector> createState() => _SubjectSelectorState();
}

class _SubjectSelectorState extends State<SubjectSelector>
    with TickerProviderStateMixin {
  late SubjectIdentity? _selectedSubject;
  late AnimationController _animationController;
  late AnimationController _staggerController;
  int? _hoveredIndex;
  int? _pressedIndex;

  @override
  void initState() {
    super.initState();
    _selectedSubject = widget.initialSubject;
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _staggerController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _staggerController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    _staggerController.dispose();
    super.dispose();
  }

  void _selectSubject(SubjectIdentity subject) {
    if (_selectedSubject?.id == subject.id) return;
    setState(() {
      _selectedSubject = subject;
    });
    widget.onSubjectChanged(subject);
    _animationController.forward(from: 0);
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final subjects = SubjectIdentities.all;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          t.subjectLabel,
          style: const TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 17,
            color: AppColors.ink,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          t.subjectHint,
          style: const TextStyle(
            fontSize: 13,
            color: AppColors.inkSoft,
          ),
        ),
        const SizedBox(height: 16),
        _buildSubjectGrid(subjects),
        if (_selectedSubject != null) ...[
          const SizedBox(height: 16),
          _buildSelectedSubjectBanner(),
        ],
      ],
    );
  }

  Widget _buildSubjectGrid(List<SubjectIdentity> subjects) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth > 600 ? 4 : 2;
        final childAspectRatio = constraints.maxWidth > 600 ? 1.1 : 1.0;

        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            childAspectRatio: childAspectRatio,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
          ),
          itemCount: subjects.length,
          itemBuilder: (context, index) {
            final subject = subjects[index];
            final isSelected = _selectedSubject?.id == subject.id;
            return _SubjectCard(
              key: ValueKey(subject.id),
              subject: subject,
              isSelected: isSelected,
              isHovered: _hoveredIndex == index,
              isPressed: _pressedIndex == index,
              templateCount: widget.templateCount,
              showTemplateCount: widget.showTemplateCount,
              staggerDelay: index * 50,
              staggerController: _staggerController,
              onTap: () => _selectSubject(subject),
              onHover: (hovering) {
                setState(() {
                  _hoveredIndex = hovering ? index : null;
                });
              },
              onLongPressStart: () {
                setState(() => _pressedIndex = index);
              },
              onLongPressEnd: () {
                setState(() => _pressedIndex = null);
              },
            );
          },
        );
      },
    );
  }

  Widget _buildSelectedSubjectBanner() {
    final subject = _selectedSubject!;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: subject.backgroundGradient,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: subject.mediumBorder, width: 1.5),
        boxShadow: [
          BoxShadow(
            color: subject.primaryColor.withValues(alpha: 0.15),
            blurRadius: 16,
            offset: const Offset(0, 4),
            spreadRadius: -2,
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: subject.primaryColor,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(subject.icon, color: Colors.white, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  subject.name,
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                    color: subject.primaryColor,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subject.description,
                  style: TextStyle(
                    fontSize: 13,
                    color: subject.primaryColor.withValues(alpha: 0.8),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Icon(
            Icons.check_circle_rounded,
            color: subject.primaryColor,
            size: 28,
          ),
        ],
      ),
    );
  }
}


class _SubjectCard extends StatefulWidget {
  final SubjectIdentity subject;
  final bool isSelected;
  final bool isHovered;
  final bool isPressed;
  final int? templateCount;
  final bool showTemplateCount;
  final int staggerDelay;
  final AnimationController staggerController;
  final VoidCallback onTap;
  final ValueChanged<bool> onHover;
  final VoidCallback onLongPressStart;
  final VoidCallback onLongPressEnd;

  const _SubjectCard({
    super.key,
    required this.subject,
    required this.isSelected,
    required this.isHovered,
    required this.isPressed,
    this.templateCount,
    required this.showTemplateCount,
    required this.staggerDelay,
    required this.staggerController,
    required this.onTap,
    required this.onHover,
    required this.onLongPressStart,
    required this.onLongPressEnd,
  });

  @override
  State<_SubjectCard> createState() => _SubjectCardState();
}

class _SubjectCardState extends State<_SubjectCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _scaleController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _staggerAnimation;

  @override
  void initState() {
    super.initState();
    _scaleController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.97).animate(
      CurvedAnimation(parent: _scaleController, curve: Curves.easeOutCubic),
    );

    _staggerAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: widget.staggerController,
        curve: Interval(
          (widget.staggerDelay / 1000).clamp(0.0, 0.5),
          ((widget.staggerDelay + 300) / 1000).clamp(0.0, 1.0),
          curve: Curves.easeOutCubic,
        ),
      ),
    );

    widget.staggerController.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _staggerAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
          CurvedAnimation(
            parent: widget.staggerController,
            curve: Interval(
              (widget.staggerDelay / 1000).clamp(0.0, 0.5),
              ((widget.staggerDelay + 300) / 1000).clamp(0.0, 1.0),
              curve: Curves.easeOutCubic,
            ),
          ),
        );
      }
    });
  }

  @override
  void dispose() {
    _scaleController.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails details) {
    _scaleController.forward();
    widget.onLongPressStart();
  }

  void _handleTapUp(TapUpDetails details) {
    _scaleController.reverse();
    widget.onLongPressEnd();
  }

  void _handleTapCancel() {
    _scaleController.reverse();
    widget.onLongPressEnd();
  }

  @override
  Widget build(BuildContext context) {
    final subject = widget.subject;
    final isSelected = widget.isSelected;
    final isHovered = widget.isHovered && !isSelected;
    final isPressed = widget.isPressed;

    return AnimatedBuilder(
      animation: Listenable.merge([_scaleAnimation, _staggerAnimation]),
      builder: (context, child) {
        final scale = _scaleAnimation.value;
        final stagger = _staggerAnimation.value;

        return Transform.translate(
          offset: Offset(0, (1 - stagger) * 30),
          child: Opacity(
            opacity: stagger,
            child: Transform.scale(
              scale: isPressed ? 0.97 : scale,
              child: MouseRegion(
                onEnter: (_) => widget.onHover(true),
                onExit: (_) => widget.onHover(false),
                child: GestureDetector(
                  onTapDown: _handleTapDown,
                  onTapUp: _handleTapUp,
                  onTapCancel: _handleTapCancel,
                  onTap: widget.onTap,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    curve: Curves.easeOutCubic,
                    decoration: BoxDecoration(
                      gradient: isSelected
                          ? LinearGradient(
                              colors: [
                                subject.primaryColor.withValues(alpha: 0.12),
                                subject.primaryColor.withValues(alpha: 0.06),
                              ],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            )
                          : null,
                      color: isSelected ? null : AppColors.white,
                      borderRadius: BorderRadius.circular(subject.borderRadius),
                      border: Border.all(
                        color: isSelected
                            ? subject.strongBorder
                            : isHovered
                                ? subject.mediumBorder
                                : AppColors.border,
                        width: isSelected ? 2 : (isHovered ? 1.5 : 1),
                      ),
                      boxShadow: [
                        if (isHovered && !isSelected)
                          BoxShadow(
                            color: subject.primaryColor.withValues(alpha: 0.15),
                            blurRadius: 16,
                            offset: const Offset(0, 8),
                            spreadRadius: -4,
                          )
                        else if (isSelected)
                          subject.cardShadow
                        else
                          BoxShadow(
                            color: AppColors.ink.withValues(alpha: 0.04),
                            blurRadius: 12,
                            offset: const Offset(0, 2),
                          ),
                      ],
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _buildIconArea(subject, isSelected, isHovered),
                          const SizedBox(height: 12),
                          _buildTitleArea(subject, isSelected),
                          const SizedBox(height: 4),
                          _buildDescriptionArea(subject, isSelected),
                          if (widget.showTemplateCount && widget.templateCount != null)
                            _buildTemplateCount(subject, widget.templateCount!),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildIconArea(SubjectIdentity subject, bool isSelected, bool isHovered) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        gradient: isSelected
            ? LinearGradient(
                colors: [subject.primaryColor, subject.secondaryColor],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : LinearGradient(
                colors: [
                  subject.primaryColor.withValues(alpha: isHovered ? 0.15 : 0.1),
                  subject.secondaryColor.withValues(alpha: isHovered ? 0.1 : 0.05),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: isSelected
            ? [
                BoxShadow(
                  color: subject.primaryColor.withValues(alpha: 0.3),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ]
            : null,
      ),
      child: Icon(
        subject.icon,
        color: isSelected ? Colors.white : subject.primaryColor,
        size: 28,
      ),
    );
  }

  Widget _buildTitleArea(SubjectIdentity subject, bool isSelected) {
    return Text(
      subject.name,
      style: TextStyle(
        fontWeight: FontWeight.w700,
        fontSize: 15,
        color: isSelected ? subject.primaryColor : AppColors.ink,
        height: 1.2,
      ),
      textAlign: TextAlign.center,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }

  Widget _buildDescriptionArea(SubjectIdentity subject, bool isSelected) {
    return Text(
      subject.description,
      style: TextStyle(
        fontSize: 11,
        color: isSelected
            ? subject.primaryColor.withValues(alpha: 0.8)
            : AppColors.inkSoft,
        fontWeight: FontWeight.w500,
        height: 1.2,
      ),
      textAlign: TextAlign.center,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }

  Widget _buildTemplateCount(SubjectIdentity subject, int count) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: subject.primaryColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.layers_rounded,
              size: 12,
              color: subject.primaryColor,
            ),
            const SizedBox(width: 4),
            Text(
              '$count templates',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: subject.primaryColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}


class CompactSubjectSelector extends StatelessWidget {
  final SubjectIdentity? selectedSubject;
  final ValueChanged<SubjectIdentity> onSubjectChanged;
  final List<SubjectIdentity> availableSubjects;

  const CompactSubjectSelector({
    super.key,
    this.selectedSubject,
    required this.onSubjectChanged,
    this.availableSubjects = const [],
  });

  @override
  Widget build(BuildContext context) {
    final subjects = availableSubjects.isEmpty
        ? SubjectIdentities.all
        : availableSubjects;

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: subjects.map((subject) {
        final isSelected = selectedSubject?.id == subject.id;
        return _CompactSubjectChip(
          subject: subject,
          isSelected: isSelected,
          onTap: () => onSubjectChanged(subject),
        );
      }).toList(),
    );
  }
}

class _CompactSubjectChip extends StatefulWidget {
  final SubjectIdentity subject;
  final bool isSelected;
  final VoidCallback onTap;

  const _CompactSubjectChip({
    required this.subject,
    required this.isSelected,
    required this.onTap,
  });

  @override
  State<_CompactSubjectChip> createState() => _CompactSubjectChipState();
}

class _CompactSubjectChipState extends State<_CompactSubjectChip>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final subject = widget.subject;
    final isSelected = widget.isSelected;

    return GestureDetector(
      onTapDown: (_) => _controller.forward(),
      onTapUp: (_) => _controller.reverse(),
      onTapCancel: () => _controller.reverse(),
      onTap: widget.onTap,
      child: AnimatedBuilder(
        animation: _scaleAnimation,
        builder: (context, child) {
          return Transform.scale(
            scale: _scaleAnimation.value,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                gradient: isSelected
                    ? LinearGradient(
                        colors: [subject.primaryColor, subject.secondaryColor],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: isSelected ? null : AppColors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isSelected
                      ? subject.strongBorder
                      : subject.mediumBorder,
                  width: isSelected ? 2 : 1,
                ),
                boxShadow: isSelected
                    ? [
                        BoxShadow(
                          color: subject.primaryColor.withValues(alpha: 0.25),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                          spreadRadius: -2,
                        ),
                      ]
                    : null,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    subject.icon,
                    size: 16,
                    color: isSelected ? Colors.white : subject.primaryColor,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    subject.name,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                      color: isSelected ? Colors.white : subject.primaryColor,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}