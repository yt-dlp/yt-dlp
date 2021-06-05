// input: []
// output: 123

package {
public class NeOperator {
    public static function main(): int {
        var res:int = 0;
        if (1 != 2) {
            res += 3;
        } else {
            res += 4;
        }
        if (2 != 2) {
            res += 10;
        } else {
            res += 20;
        }
        if (9 == 9) {
            res += 100;
        }
        return res;
    }
}
}
