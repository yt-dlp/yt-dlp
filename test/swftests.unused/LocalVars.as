// input: [1, 2]
// output: 3

package {
public class LocalVars {
    public static function main(a:int, b:int):int{
        var c:int = a + b + b;
        var d:int = c - b;
        var e:int = d;
        return e;
    }
}
}
