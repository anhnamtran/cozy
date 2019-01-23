import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.concurrent.ThreadLocalRandom;

class AggMain {
  public static void main(String[] args) {
    Agg b = new Agg(); // cozy generated

    ArrayList<Integer> s = new ArrayList<Integer>(); // baseline

    // items
    Integer N = 10000;

    // random number limit
    Integer M = 1000000;

    ArrayList<Integer> to_add = new ArrayList<Integer>();

    ArrayList<Integer> sum_bs = new ArrayList<Integer>();
    ArrayList<Integer> count_bs = new ArrayList<Integer>();

    ArrayList<Integer> sum_ss = new ArrayList<Integer>();
    ArrayList<Integer> count_ss = new ArrayList<Integer>();

    for (int i = 0; i < N; i++) {
      to_add.add(ThreadLocalRandom.current().nextInt(0, M));
    }

    long lStartTime = System.nanoTime();
    for (int i = 0; i < N; i++) {
      b.add(to_add.get(i));

      sum_bs.add(b.totalSum());
      count_bs.add(b.countGt10());

      b.add(to_add.get(i));

      sum_bs.add(b.totalSum());
      count_bs.add(b.countGt10());
    }

    System.out.println("Synthesized code time in ms: " + (System.nanoTime() - lStartTime) / 1000000);

    lStartTime = System.nanoTime();
    for (int i = 0; i < N; i++) {
      s.add(to_add.get(i));

      sum_ss.add(sum(s));
      count_ss.add(countGt10(s));

      s.add(to_add.get(i));

      sum_ss.add(sum(s));
      count_ss.add(countGt10(s));
    }

    System.out.println("Baseline code time in ms: " + (System.nanoTime() - lStartTime) / 1000000);

    for (int i = 0; i < N; i++) {
      assert sum_bs.get(i) == sum_ss.get(i);
      assert count_bs.get(i) == count_ss.get(i);
    }
  }
  
  public static Integer sum(ArrayList<Integer> ls) {
    Integer sum = 0;
    for (int i = 0; i < ls.size(); i++) {
      sum += ls.get(i);
    }
    return sum;
  }

  public static Integer countGt10(ArrayList<Integer> ls) {
    Integer count = 0;
    for (int i = 0; i < ls.size(); i++) {
      if (ls.get(i).compareTo(10) > 0)
        count++;
    }
    return count;
  }
}
