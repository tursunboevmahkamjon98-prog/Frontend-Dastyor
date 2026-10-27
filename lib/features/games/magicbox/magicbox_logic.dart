import 'dart:math';









class BoxState {
  final int id;
  int position;
  final int questionIndex;

  BoxState({required this.id, required this.position, required this.questionIndex});
}

const kBoxCount = 3;
const kStartingLives = 3;
const kPointsPerAnswer = 100;




class SwapStep {
  final int a;
  final int b;
  const SwapStep(this.a, this.b);
}

const _pairs = [SwapStep(0, 1), SwapStep(1, 2), SwapStep(0, 2)];

const _allPerms = [
  [0, 1, 2],
  [0, 2, 1],
  [1, 0, 2],
  [1, 2, 0],
  [2, 0, 1],
  [2, 1, 0],
];

int _parity(List<int> p) {
  var inv = 0;
  for (var i = 0; i < p.length; i++) {
    for (var j = i + 1; j < p.length; j++) {
      if (p[i] > p[j]) inv++;
    }
  }
  return inv % 2;
}

List<int> _walkPerm(List<SwapStep> plan) {
  final p = [0, 1, 2];
  for (final s in plan) {
    final t = p[s.a];
    p[s.a] = p[s.b];
    p[s.b] = t;
  }
  return p;
}

List<SwapStep> _randomWalk(int length, Random rng) {
  final plan = <SwapStep>[];
  var last = -1;
  for (var i = 0; i < length; i++) {
    
    
    
    var next = rng.nextInt(_pairs.length);
    while (next == last) {
      next = rng.nextInt(_pairs.length);
    }
    last = next;
    plan.add(_pairs[next]);
  }
  return plan;
}












List<SwapStep> planShuffle(int swaps, Random rng) {
  final target = _allPerms[rng.nextInt(_allPerms.length)];
  final length = _parity(target) == swaps % 2 ? swaps : swaps + 1;
  for (var attempt = 0; attempt < 200; attempt++) {
    final plan = _randomWalk(length, rng);
    final got = _walkPerm(plan);
    if (got[0] == target[0] && got[1] == target[1] && got[2] == target[2]) {
      return plan;
    }
  }
  
  return _randomWalk(length, rng);
}



void applySwap(List<BoxState> boxes, SwapStep step) {
  for (final b in boxes) {
    if (b.position == step.a) {
      b.position = step.b;
    } else if (b.position == step.b) {
      b.position = step.a;
    }
  }
}



List<int> randomOrder(int n, Random rng) {
  final a = List<int>.generate(n, (i) => i);
  for (var i = a.length - 1; i > 0; i--) {
    final j = rng.nextInt(i + 1);
    final t = a[i];
    a[i] = a[j];
    a[j] = t;
  }
  return a;
}




({int swaps, int swapMs}) roundConfig(int roundIndex) => (
      swaps: min(9, 3 + (roundIndex * 0.7).floor()),
      swapMs: max(280, 640 - roundIndex * 42),
    );



int scoreFor(int streakAfter) {
  final combo = 1 + (streakAfter ~/ 3) * 0.5;
  return (kPointsPerAnswer * combo).round();
}
