// input: []
// output: 121

package {
public class ClassCall {
    public static function main():int{
    	var f:OtherClass = new OtherClass();
        return f.func(100,20);
    }
}
}

class OtherClass {
	public function func(x: int, y: int):int {
		return x+y+1;
	}
}
