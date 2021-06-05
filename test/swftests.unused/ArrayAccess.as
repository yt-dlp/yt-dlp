// input: [["a", "b", "c", "d"]]
// output: ["c", "b", "a", "d"]

package {
public class ArrayAccess {
    public static function main(ar:Array):Array {
    	var aa:ArrayAccess = new ArrayAccess();
    	return aa.f(ar, 2);
    }

    private function f(ar:Array, num:Number):Array{
        var x:String = ar[0];
        var y:String = ar[num % ar.length];
        ar[0] = y;
        ar[num] = x;
        return ar;
    }
}
}
