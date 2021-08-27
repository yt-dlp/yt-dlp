// input: []
// output: 4

package {
public class ConstArrayAccess {
	private static const x:int = 2;
	private static const ar:Array = ["42", "3411"];

    public static function main():int{
        var c:ConstArrayAccess = new ConstArrayAccess();
        return c.f();
    }

    public function f(): int {
    	return ar[1].length;
    }
}
}
