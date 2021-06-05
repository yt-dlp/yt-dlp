// input: []
// output: 1

package {
public class StaticRetrieval {
	public static var v:int;

    public static function main():int{
        if (v) {
        	return 0;
        } else {
        	return 1;
        }
    }
}
}
